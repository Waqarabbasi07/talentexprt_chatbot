import os
import time
import textract
import asyncio
import openai
from config import OPENAI_API_KEY
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
import re
import json
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from dotenv import load_dotenv
import os
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

class FolderPathRequest(BaseModel):
    folder_path: str


llm = init_chat_model("gpt-4o-mini", model_provider="openai")

def get_prompt(content: str) -> str:
    return f"""
    As a CURRICULUM VITAE Parser, extract all relevant information from the CV content below:

    {content}

    Provide the extracted information in the following JSON format:
    {{
        "firstName": "",
        "lastName": "",
        "email": "",
        "mobile": "",
        "about": "",
        "profilePicture": "",
        "title": null,
        "zip": "",
        "street": "",
        "address": "",
        "websiteLink": "",
        "education": [
            {{
                "institution": "",
                "degree": "",
                "date": ""
            }}
        ],
        "experience": [
            {{
                "companyName": "",
                "role": "",
                "startDate": "",
                "endDate": "",
                "description": ""
            }}
        ],
        "skills": []
    }}

    ### Instructions:
    - Extract `firstName` and `lastName` separately.
    - Extract `email` and `mobile` from the contact details.
    - NOTE: Extract `about` as formated HTML content if available and must in p_tag of a <div>.
    - `profilePicture`, `title`, `zip`, `street`, `address`, and `websiteLink` should be empty strings if not provided.
    - Extract `education` with `institution`, `degree`, and `date` (graduation date or completion date ) should be in this format(yyyy-mm-dd).
    - Extract `experience` with `companyName`, `role`, `startDate`, `endDate`, and `description` any date should be in this format(yyyy-mm-dd).
    - Extract `skills` as an array of strings.
    - Ensure the response is in proper JSON format.
    - If any field is missing, use an empty string `""`.

    Return the extracted details strictly in the given format.
    """

# async def process_file(file_path: str):
#     try:
#         content_bytes = textract.process(file_path)
#         content = content_bytes.decode("utf-8").strip()
#         print("**************content*******",content)
#         prompt = get_prompt(content)
#         response = await asyncio.to_thread(llm.invoke, prompt)

#         parsed_data = response.content if hasattr(response, "content") else str(response)

#         parsed_data = re.sub(r"```json|```", "", parsed_data).strip()


#         parsed_data = json.loads(parsed_data)

#         return {"file": os.path.basename(file_path), "parsed_data": parsed_data}
#     except Exception as e:
#         return {"file": os.path.basename(file_path), "error": str(e)}


class InvalidFileFormatException(Exception):
    """Custom exception for invalid file formats."""
    pass

async def process_file(file_path: str):
    try:
        
        # Step 1: Try extracting text using textract
        content_bytes = textract.process(file_path)
        content = content_bytes.decode("utf-8").strip()

        # Step 2: Check if content is empty or unreadable
        if not content or len(content.split()) < 5:
            # Step 3: Check if the PDF contains selectable text using pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pdf_text = "".join([page.extract_text() or "" for page in pdf.pages])

            if not pdf_text.strip():
                raise InvalidFileFormatException("CV is not in the correct format (image-based PDF detected). Please upload a text-based PDF.")

        # Step 4: If OCR is needed, apply it as a fallback
        if not content.strip():
            images = convert_from_path(file_path)
            content = "\n".join([pytesseract.image_to_string(img) for img in images]).strip()

            if not content or len(content.split()) < 5:
                raise InvalidFileFormatException("CV is not in the correct format. Unable to extract readable text.")

        # print("**************content*******", content)

        prompt = get_prompt(content)
        response = await asyncio.to_thread(llm.invoke, prompt)

        parsed_data = response.content if hasattr(response, "content") else str(response)

        parsed_data = re.sub(r"```json|```", "", parsed_data).strip()
        parsed_data = json.loads(parsed_data)

        return {"file": os.path.basename(file_path), "parsed_data": parsed_data}

    except InvalidFileFormatException as e:
        raise HTTPException(status_code=400, detail=str(e))  # Return proper error in FastAPI

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")  # Other errors
async def process_all_resumes(folder_path: str):
    tasks = []
    
    if not os.path.exists(folder_path):
        return {"error": "Folder path does not exist"}
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            tasks.append(process_file(file_path))

    return await asyncio.gather(*tasks)


@app.post("/cv_parser")
async def cv_parser(request: FolderPathRequest):
    folder_path = request.folder_path 
    if not folder_path:
        raise HTTPException(status_code=400, detail="Folder path is required")
    
    start_time = time.perf_counter()
    
    results = await process_all_resumes(folder_path)

    elapsed_time = time.perf_counter() - start_time
    response_data = {
        "message": f"All files processed in {elapsed_time:.2f} seconds.",
        "results": results
    }

    return json.loads(json.dumps(response_data, ensure_ascii=False, separators=(',', ':')))



# import os
# import time
# import textract
# import asyncio
# import openai
# import requests
# import json
# import re
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from langchain.chat_models import init_chat_model
# from dotenv import load_dotenv

# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], 
#     allow_credentials=True,
#     allow_methods=["*"],  
#     allow_headers=["*"],
# )

# class FileURLRequest(BaseModel):
#     fileUrl: str  # Expecting a URL to download the file

# llm = init_chat_model("gpt-4o-mini", model_provider="openai")

# def get_prompt(content: str) -> str:
#     return f"""
#     As a CURRICULUM VITAE Parser, extract all relevant information from the CV content below:

#     {content}

#     Provide the extracted information in the following JSON format:
#     {{
#         "firstName": "","profilePicture": "",
#         "title": null,
#         "zip": "",
#         "street": "",
#         "address": "",
#         "websiteLink": "",
#         "lastName": "",
#         "email": "",
#         "mobile": "",
#         "about": "",
#         "profilePicture": "",
#         "title": null,
#         "zip": "",
#         "street": "",
#         "address": "",
#         "websiteLink": "",
#         "education": [
#             {{
#                 "institution": "",
#                 "degree": "",
#                 "date": ""
#             }}
#         ],
#         "experience": [
#             {{
#                 "companyName": "",
#                 "role": "",
#                 "startDate": "",
#                 "endDate": "",
#                 "description": ""
#             }}
#         ],
#         "skills": []
#     }}

#     ### Instructions:
#     - Extract `firstName` and `lastName` separately.
#     - Extract `email` and `mobile` from the contact details.
#     - NOTE: Extract `about` as formatted HTML content if available and in p_tag of a <div>.
#     - `profilePicture`, `title`, `zip`, `street`, `address`, and `websiteLink` should be empty strings if not provided.
#     - Extract `education` with `institution`, `degree`, and `date` (graduation date or completion date ) in this format (yyyy-mm-dd).
#     - Extract `experience` with `companyName`, `role`, `startDate`, `endDate`, and `description`. Any date should be in this format (yyyy-mm-dd).
#     - Extract `skills` as an array of strings.
#     - Ensure the response is in proper JSON format.
#     - If any field is missing, use an empty string `""`.

#     Return the extracted details strictly in the given format.
#     """

# async def download_pdf(file_url: str, save_path: str):
#     """Downloads the PDF file from the provided URL."""
#     try:
#         response = requests.get(file_url, stream=True)
#         response.raise_for_status()  

#         with open(save_path, "wb") as pdf_file:
#             for chunk in response.iter_content(chunk_size=8192):
#                 pdf_file.write(chunk)

#         return save_path
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=400, detail=f"Failed to download file: {str(e)}")

# async def process_file(file_url: str):
#     """Downloads and processes the PDF file."""
#     try:
#         temp_filename = f"temp_{int(time.time())}.pdf"
#         temp_file_path = os.path.join("/tmp", temp_filename)  # Use a temp directory

#         # Step 1: Download PDF
#         pdf_path = await download_pdf(file_url, temp_file_path)

#         # Step 2: Extract text from PDF
#         content_bytes = textract.process(pdf_path)
#         content = content_bytes.decode("utf-8").strip()

#         # Step 3: Generate prompt and call LLM
#         prompt = get_prompt(content)
#         response = await asyncio.to_thread(llm.invoke, prompt)

#         parsed_data = response.content if hasattr(response, "content") else str(response)
#         parsed_data = re.sub(r"```json|```", "", parsed_data).strip()

#         parsed_data = json.loads(parsed_data)

#         # Clean up the temp file
#         os.remove(pdf_path)

#         return {"file": os.path.basename(pdf_path), "parsed_data": parsed_data}
#     except Exception as e:
#         return {"error": str(e)}

# @app.post("/cv_parser")
# async def cv_parser(request: FileURLRequest):
#     """Handles requests for parsing a CV PDF from a given URL."""
#     file_url = request.fileUrl
#     if not file_url:
#         raise HTTPException(status_code=400, detail="File URL is required")
    
#     start_time = time.perf_counter()
    
#     result = await process_file(file_url)

#     elapsed_time = time.perf_counter() - start_time
#     response_data = {
#         "message": f"File processed in {elapsed_time:.2f} seconds.",
#         "result": result
#     }

#     return json.loads(json.dumps(response_data, ensure_ascii=False, separators=(',', ':')))
