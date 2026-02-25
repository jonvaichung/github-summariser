# GitHub Repository Summariser API

This mini project uses a FastAPI service to analyse GitHub repositories using Nebius AI. It returns a structured JSON summary containing the project description, technologies used, and file structure, allowing the user to quickly understand contents within a GitHub repository. 

## Features
- **Quick Summarisation:** Uses **meta-llama/Llama-3.3-70B-Instruct-fast** for reliable and fast repo analysis
- **Optimised Performance:** Filters only the necessary repo files and truncates the `README.md` file for saving LLM tokens and cost - able to handle large repos as a result. 
- **Error Handling:** Provides valid JSON output even in failure states.




## Step-by-step Setup Instructions

Follow these steps to run the project locally.

### 1. Prerequisites
- Python 3.10 or higher
- A [Nebius AI](https://nebius.com/) API Key
- A GitHub Personal Access Token

### 2. Installation
Clone the repository and navigate to the project folder:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` and add your keys
```text
NEBIUS_API_KEY="your_nebius_api_key_here"
GITHUB_TOKEN="your_github_token_here"
```
### 4. Run the API

Start the server using Uvicorn: 

```bash
uvicorn main:app --reload
```
Open the API at `http://127.0.0.1:8000`. 

## API Usage

**Endpoint:** `POST /summarize`

Request Example: 

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/summarize' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "github_url": "https://github.com/microsoft/AI-For-Beginners"
}'
```

Response Example: 
```json
{
  "summary": "The project is a 12-week, 24-lesson curriculum for beginners to learn Artificial Intelligence (AI), covering tools like TensorFlow and PyTorch, as well as ethics in AI. It includes practical lessons, quizzes, and labs, and is available in over 50 languages.",
  "technologies": [
    "Python",
    "TensorFlow",
    "PyTorch"
  ],
  "structure": "The project is organized into several folders, including lessons, data, and translations, with a focus on readability and accessibility, and includes a range of files such as Markdown documents, images, and YAML configuration files."
}
```

## Project Notes

**Model Selection**: In this project, I used **meta-llama/Llama-3.3-70B-Instruct-fast**. It was able to provide very fast/good responses and was able to follow the system prompt instructions very accurately. Overall, this model was very reliable, and considerably cheaper incomparison to the **Azure OpenAI GPT models** that I am used to using. However, there were even cheaper options provided by Nebius such as **Meta-Llama-3.1-8B-Instruct** that could have potentially completed this task too!

**Repo Content Handling and Context Management**: To be able to handle all types of repositories, I only got the `Root File Tree` and the `README.md`. This we able to provide enough context for the project to be understood in terms of: what the project was about, what technologies were used, and what the structure was. I used `should_include_file` fucntion to be able to filter out any unwanted files such as `.png`, `.jpg` , `.lock` files, as well as truncated the `README.md` content to 5000 characters in an attempt to minimise the token usage by the LLM (in the case where the repo was very large). 


