import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from config import OPENAI_API_KEY
from fastapi.responses import HTMLResponse
import json
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Union, List
import re
import markdown
from fastapi.responses import JSONResponse
 
client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(root_path="/api1")

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

class TestModel(BaseModel):
    job_description: str
    proposals: Dict[str, str]


def openaiAI_bio(prompt: str):
    bio_prompt = f'''
    Generate a JSON response for a {prompt} with two keys:
    1. "professionalBio": A compelling bio following the structure below
    2. "coreSkills": An array of 8-10 most relevant skills for this role

    BIO STRUCTURE:
    - Problem Statement (20 words)
    - Solution Offering (50 words)
    - Proof & Expertise (30 words)
    - Call to Action (20 words)

    RESPONSE FORMAT (Return only this JSON, no extra text or explanations):
    {{
        "professionalBio": "Your well-structured bio here...",
        "coreSkills": ["Skill 1", "Skill 2", ...]
    }}
    '''
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": bio_prompt}],
            max_tokens=150,
        )

        response_text = response.choices[0].message.content.strip()
        
        try:
            # Ensure response is a valid JSON (Extract JSON if extra text exists)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON found in response.")

            json_data = response_text[json_start:json_end]
            bio_data = json.loads(json_data)

            if "professionalBio" not in bio_data or "coreSkills" not in bio_data:
                raise ValueError("Missing expected JSON keys.")

            bio_data["professionalBio"] = f"<div>{markdown.markdown(bio_data['professionalBio'])}</div>"



            return JSONResponse(content=bio_data, status_code=200)

        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Invalid JSON response: {response_text}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")



def openaiAI_jd(prompt: str):
    jd_prompt = f"""
    As an expert Upwork job description writer, create a **compelling** job posting in **valid JSON format** with the following structure:

    {{
        "projectOverview": "Concise and engaging project introduction (50-70 words)",
        "requirements": ["List key qualifications and skills"],
        "deliverables": ["List expected deliverables"],
        "callToAction": "Clear final statement encouraging applications"
    }}

    - **Keep the response strictly in JSON format**
    - **Do not include any additional text, headers, or explanations**
    - **Ensure all fields are present and properly formatted**

    Job Posting Input: {prompt}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": jd_prompt}],
            max_tokens=400,  # Increased from 150 to 400 to prevent truncation
        )

        response_text = response.choices[0].message.content.strip()
        print("response_text", response_text)

        # Attempt to extract JSON
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON found in response.")

        json_data = response_text[json_start:json_end]

        try:
            jd_data = json.loads(json_data)

            required_keys = ["projectOverview", "requirements", "deliverables", "callToAction"]
            if not all(k in jd_data for k in required_keys):
                raise ValueError("Missing expected JSON keys.")

            html_content = f"""
            <div class="container">
                
                
                <p>{jd_data["projectOverview"]}</p>
                <h5>Requirements</h5>
                <ul>
                    {"".join(f"<li>{req}</li>" for req in jd_data["requirements"])}
                </ul>
                <h5>Deliverables</h5>
                <ul>
                    {"".join(f"<li>{deliverable}</li>" for deliverable in jd_data["deliverables"])}
                </ul>
                
            </div>
            """

            return HTMLResponse(content=html_content.strip(), status_code=200)

        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Invalid JSON response: {response_text}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


def openaiAI_proposal(prompt: str):
    proposal_prompt = f"""
    Analyze the following job posting and create a focused proposal in **valid JSON format**:

    {{
        "proposalTitle": "Title of the proposal",
        "introduction": "A concise intro addressing the client's needs",
        "pastProjects": ["Highlight 2-3 relevant past projects with impact metrics"],
        "technicalApproach": "Describe the solution approach for this project",
        "implementationMethodology": ["Phase-wise breakdown of implementation"],
        "callToAction": "Encouraging statement to conclude"
    }}

    - **Ensure the response is valid JSON (NO extra text, no markdown)**
    - **Do NOT wrap the response in backticks or markdown formatting**
    - **Return only the JSON object, without explanations**

    Job Posting Input: {prompt}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": proposal_prompt}],
            max_tokens=400,  # Increased from 200 to 400 to prevent truncation
        )

        response_text = response.choices[0].message.content.strip()
        print("response_text", response_text)

        # Extract JSON
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON found in response.")

        json_data = response_text[json_start:json_end]

        try:
            proposal_data = json.loads(json_data)

            required_keys = ["proposalTitle", "introduction", "pastProjects", "technicalApproach", "implementationMethodology", "callToAction"]
            if not all(k in proposal_data for k in required_keys):
                raise ValueError("Missing expected JSON keys.")

            # Convert response into formatted HTML
            html_content = f"""
            <div class="container">
            
                
                <p>{proposal_data["introduction"]}</p>
                <h5>Past Projects</h5>
                <ul>
                    {"".join(f"<li>{project}</li>" for project in proposal_data["pastProjects"])}
                </ul>
                <h5>Technical Approach</h5>
                <p>{proposal_data["technicalApproach"]}</p>
                <h5>Implementation Methodology</h5>
                <ul>
                    {"".join(f"<li>{method}</li>" for method in proposal_data["implementationMethodology"])}
                </ul>
                
            </div>
            """
            return HTMLResponse(content=html_content.strip(), status_code=200)

        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Invalid JSON response: {response_text}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")



# Custom type for proposals keys
ProposalKey = Union[str, int]

class TestModel(BaseModel):
    job_description: str
    proposals: Dict[ProposalKey, str]

    @validator('proposals', pre=True)
    def convert_keys_to_str(cls, value):
        # Convert all keys to strings to handle both str and int keys
        if isinstance(value, dict):
            return {str(key): val for key, val in value.items()}
        return value

def openAI_recommender(job_description: str, proposals: Dict[str, str]) -> List[int]:
    """
    Processes Upwork proposals and returns a list of user_ids sorted by AI recommendation.

    Args:
        job_description: A string containing the job description.
        proposals: A dictionary where keys are user IDs and values are proposal texts.

    Returns:
        List of user_ids sorted based on AI recommendation.
    """
    try:
        # Ensure all values are strings
        for key, value in proposals.items():
            if not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"Invalid proposal format under user_id {key}.")

        # Prepare the analysis prompt
        analysis_prompt = f"""
        Job Description:
        {job_description}

        Proposals:
        {json.dumps(proposals, indent=2)}

        Task: Review these Proposals and select the best candidates based on the Job Description.

        ### **Evaluation Criteria:**
        **Technical:**  
        - Required skills match  
        - Technical expertise level  
        - Relevant tools/technology  

        **Non-technical:**  
        - Communication style  
        - Project management  
        - Problem-solving approach  

        **Practical:**  
        - Rate/budget  
        - Timeline  
        - Past work samples  

        ### **Output Format:**  
        Return a **JSON array** of `user_id` (integers), ranked by suitability.  
        **Ensure the output is ONLY a JSON array of integers, NO extra text or formatting.**  
        **Do NOT include explanations, markdown, or any text outside of the JSON array.**  

        Example output:  
        [101, 203, 456, 789]
        """

        # Assuming client is defined earlier for API request
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": analysis_prompt}],
            max_tokens=350,
        )
        output = response.choices[0].message.content.strip()

        try:
            # Extract only the JSON array if extra text exists
            json_start = output.find('[')
            json_end = output.rfind(']') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON array found in response.")

            json_data = output[json_start:json_end]

            # Parse JSON array
            user_ids = json.loads(json_data)

            # Ensure user_ids is a valid list of integers
            if not isinstance(user_ids, list) or not all(isinstance(uid, int) for uid in user_ids):
                raise ValueError("Response is not a valid JSON array of integers.")

            return {"top_proposal": user_ids}

        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Invalid JSON response: {output}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/generate_bio")
async def generate_bio(request: PromptRequest):
    return openaiAI_bio(request.prompt)

@app.post("/generate_jd")
async def generate_jd(request: PromptRequest):
    return openaiAI_jd(request.prompt)

@app.post("/generate_proposal")
async def generate_proposal(request: PromptRequest):
    return openaiAI_proposal(request.prompt)

@app.post("/generate_top_proposal")
async def generate_top_proposal(request: TestModel):
    return openAI_recommender(request.job_description, request.proposals)
