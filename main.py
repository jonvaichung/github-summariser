import os
import base64
import json
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Environment variables 
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY") 

# Initialising fast api app and AI client
app = FastAPI()

client = AsyncOpenAI(
    api_key=NEBIUS_API_KEY,
    base_url="https://api.tokenfactory.nebius.com/v1/"
)

# Error handling 
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": f"Internal Server Error: {str(exc)}"},
    )

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )

# RepoRequest class
class RepoRequest(BaseModel):
    github_url: str

# Filtering function to reduce token usage
def should_include_file(filename: str) -> bool:
    """
    Filters out binary files and assets to save AI tokens.
    """
    ignored_extensions = {'.png', '.jpg', '.gif', '.zip', '.exe', '.pyc', '.lock'}
    if filename.startswith('.'): return False # Ignore hidden files like .git
    ext = os.path.splitext(filename)[1].lower()
    return ext not in ignored_extensions

# Get data from GitHub
async def get_repo_data(repo_url: str):
    """
    Fetches BOTH the README content and the root file list.
    """
    # Clean up URL to get owner and repo name
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    
    owner = parts[-2]
    repo_name = parts[-1]
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}" if GITHUB_TOKEN else None
    }

    async with httpx.AsyncClient() as http_client:
        
        # Step 1 - get the repository content 
        tree_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/"
        tree_resp = await http_client.get(tree_url, headers=headers)
        
        file_list = []
        if tree_resp.status_code == 200:
            all_files = tree_resp.json()
            # Apply filtering function
            file_list = [f["name"] for f in all_files if should_include_file(f["name"])]

        # Step 2 - get the repository README file
        readme_url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
        readme_resp = await http_client.get(readme_url, headers=headers)
        
        readme_content = ""
        if readme_resp.status_code == 200:
            data = readme_resp.json()
            readme_content = base64.b64decode(data["content"]).decode("utf-8")
        elif readme_resp.status_code == 404:
            readme_content = "No README found."
        else:
            raise HTTPException(status_code=readme_resp.status_code, detail="GitHub API Error")
            
        return readme_content, file_list

# LLM analysis
async def analyze_repo(readme_text: str, file_list: list):
    
    # Truncate the README content - reduce tokens
    truncated_readme = readme_text[:5000] 

    # List of files
    files_str = ", ".join(file_list)
    
    # System Prompt Instructions 
    system_prompt = """
    You are a technical assistant. Analyze the provided GitHub repository data.
    
    Output strictly valid JSON with these 3 keys:
    1. "summary": A clear, human-readable paragraph describing what the project does.
    2. "technologies": A list of specific languages, frameworks, or libraries detected.
    3. "structure": A brief explanation of the project structure based on the file list.
    
    Do NOT output markdown code blocks (no ```json). Return ONLY the raw JSON string.
    """

    # User Prompt Input
    user_prompt = f""" 
    Root Files (Filtered): {files_str}
    README Content (Truncated): {truncated_readme}"""
    
    try:
        response = await client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-fast",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=500 # Increased to ensure full JSON response
        )
        content = response.choices[0].message.content
        
        # Clean up if the model adds markdown
        content = content.replace("```json", "").replace("```", "").strip()
        
        # Parse String -> JSON Object
        return json.loads(content)
        
    except Exception:
        # Fallback if AI fails format
        return {
            "summary": "Analysis failed to produce valid JSON.",
            "technologies": [],
            "structure": "Unknown"
        }

# Main API Endpoint
@app.post("/summarize")
async def summarize_repo(request: RepoRequest):
    # Step 1 -  get the filtered repo content and README
    readme_content, file_list = await get_repo_data(request.github_url)
    
    # Step 2 - LLM analysis
    result = await analyze_repo(readme_content, file_list)
    
    # JSON output
    return result

@app.get("/")
def home():
    return {"message": "Service is running! Send POST to /summarize"}