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
from datetime import datetime 

client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(root_path="/api1")

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

class PromptRequest(BaseModel):
    prompt: str

class JobDescriptionRequest(BaseModel):
    job_description: str

class titleRequest(BaseModel):
    title: str
	

# Custom type for proposals keys
ProposalKey = Union[str, int]

class TestModel(BaseModel):
    job_description: str
    proposals: Dict[ProposalKey, str]

    @validator('proposals', pre=True)
    def convert_keys_to_str(cls, value):
        if isinstance(value, dict):
            return {str(key): val for key, val in value.items()}
        return value


# class TestModel(BaseModel):
#     job_description: str
#     proposals: Dict[str, str]

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

            bio_data = json.loads(json_data)  # Parse JSON

            if "professionalBio" not in bio_data or "coreSkills" not in bio_data:
                raise ValueError("Missing expected JSON keys.")

            # Convert professionalBio to HTML wrapped in a div tag
            bio_data["professionalBio"] = f"<div>{markdown.markdown(bio_data['professionalBio'])}</div>"

            return JSONResponse(content=bio_data, status_code=200)

        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Invalid JSON response: {response_text}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


def openaiAI_jd(prompt: str):
    jd_prompt = f"""
    You are an expert Upwork job-description writer.

    Task  
    Using the “Job Posting Input” provided, craft a compelling job posting in **valid JSON** with exactly this structure:

    {
    "projectOverview": "Concise, engaging overview (50–70 words)",
    "requirements": ["List of key qualifications and skills"],
    "deliverables": ["List of expected deliverables"],
    "callToAction": "Clear final statement encouraging applications"
    }

    Rules  
    • Output **only** the JSON object—no additional text, headings, or explanations.  
    • All four fields must be present and properly formatted.  
    • Adapt the language, tone, and content to fit the role described—whether technical or non-technical.

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
            model="gpt-4o-mini",
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



def openAI_contract_generator(job_description: str):

    current_date = datetime.now().strftime("%B %d, %Y")
    """
    Generates a freelance contract based on a job description using GPT-4o-mini.

    Args:
        job_description: A plain text job description.

    Returns:
        A dictionary with a 'contract' key containing the full contract text.
    """
    try:
        contract_prompt = f"""
        You are a professional contract writer. Based on the job description below, generate a complete freelance contract between a platform called **TalentExpert** and a service provider (called **TalentRequester**). The contract should include professional legal language but remain understandable and clear for both technical and non technical job discription.

        ---

        ### Constants to Use in the Contract:
        - **Client Name:** TalentExpert Client  
        - **Contractor Name:** TalentRequester  
        - **Effective Date:** {current_date}  
        - **Start Date:** TBD  
        - **End Date:** TBD  

        ---

        ### Job Description:
        {job_description}

        ---

        ### Required Contract Sections:
        1. **Parties & Effective Date**  
        2. **Scope of Work** – List the tasks and responsibilities based on the job description.  
        3. **Deliverables** – Specific, tangible outputs based on the role.  
        4. **Timeline** – Set Start/End dates to TBD and provide example milestones.  
        5. **Payment Terms** – Generic terms (you can specify placeholders for amount, schedule, and method).  
        6. **Intellectual Property Rights**  
        7. **Confidentiality Agreement**  
        8. **Termination Clause**  
        9. **Independent Contractor Status**  
        10. **Governing Law and Dispute Resolution**  
        11. "signatureSection": {{
            "TalentExpert Client": "________________________",
            "Title": "________________________",
            "Date": "________________________",
            "TalentRequester": "________________________"
        }}

        Constants to use:
        - Client Name: TalentExpert Client
        - Contractor Name: TalentRequester
        - Effective Date: {current_date}
        - Start Date: TBD
        - End Date: TBD

        Use clear headings and bullet points where appropriate. Include placeholders like `[Insert Amount]`, `[Insert State]`, etc., where specific info is needed.

        Return only the full contract text with no extra commentary. Return ONLY the JSON. No explanations. No markdown. Do not wrap with triple backticks.
       
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a legal assistant."},
                      {"role": "user", "content": contract_prompt}],
            max_tokens=1000,
        )

        contract_raw = response.choices[0].message.content.strip()

        # Extract valid JSON
        json_start = contract_raw.find('{')
        json_end = contract_raw.rfind('}') + 1

        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON found.")

        contract_json = contract_raw[json_start:json_end]
        parsed_contract = json.loads(contract_json)
        # return {"contract": parsed_contract}
        # Create HTML version
        html_contract = "<div class='contract-container'>"
        for section, content in parsed_contract.items():
            html_contract += f"<h4>{section}</h4>"
            if isinstance(content, dict):
                html_contract += "<ul>" + "".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in content.items()) + "</ul>"
            else:
                html_contract += f"<p>{content}</p>"
        html_contract += "</div>"

        return {
            "contract_html": html_contract
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating contract: {str(e)}")


def openAI_article(title: str):
    try:
        contract_prompt = f"""You are an expert writer capable of generating concise, high-quality articles. Given a title, analyze its context to determine whether it is technical or non-technical. Based on your analysis, write a well-structured, engaging article between 200 to 250 words that fits the intent of the title. Follow these instructions:

            Title Analysis: Determine whether the topic is technical (e.g., involves science, technology, programming) or non-technical (e.g., general topics, lifestyle, education, social issues).

            Tone and Language:

            For technical topics, use clear and accurate terminology appropriate for a general technical audience.

            For non-technical topics, use accessible, engaging language suitable for a broad audience.

            Structure: Write in a clear, flowing structure:

            Begin with a short introduction to the topic.

            Follow with a few informative and relevant points.

            End with a brief conclusion or insight.

            Avoid Repetition or Filler: Ensure each sentence adds value. No fluff.

            Word Count: Ensure the total article is between 200 and 250 words.

            Input Title: {title}      
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a legal assistant."},
                      {"role": "user", "content": contract_prompt}],
            max_tokens=500,
        )

        contract_raw = response.choices[0].message.content.strip()
        html_article = "<div class='article-container'>"
        for paragraph in contract_raw.split("\n\n"):
            if paragraph.strip():
                html_article += f"<p>{paragraph.strip()}</p>"
        html_article += "</div>"

        return {
            "article_html": html_article
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating article: {str(e)}")



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

@app.post("/generate_contract")
async def generate_contract(request: JobDescriptionRequest):
    return openAI_contract_generator(request.job_description)

@app.post("/generate_articals")
async def generate_articals(request: titleRequest):
    return openAI_article(request.title)

