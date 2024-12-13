import logging
import json
import random
import string
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from urllib.parse import urlparse
import asyncio

# Import custom modules from services directory
from services.config import SUPPORTED_MODELS
from services.logging_utils import setup_logging
from services.aws_utils import get_temporary_credentials, get_ec2_role, get_aws_region
from services.bedrock_service import call_bedrock
from services.transcription_service import transcribe_audio

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(root_path="/api")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

# OAuth2 scheme for token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Path to files
LLM_GENERATE_DICT_PATH = Path(__file__).parent / "pe" / "llm_generate_dict.txt"
PE_TEMPLATE_PATH = Path(__file__).parent / "pe" / "pe_template.txt"

# Generate random 8-character password with letters and numbers
chars = string.ascii_letters + string.digits
RANDOM_PASSWORD = ''.join(random.choice(chars) for _ in range(8))
logging.info(f"Generated random password for user zxxm: {RANDOM_PASSWORD}")

def read_template():
    """Read the content of pe_template.txt"""
    try:
        with open(PE_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                raise ValueError("Template file is empty")
            return content
    except Exception as e:
        logging.error(f"Error reading pe_template.txt: {e}")
        raise HTTPException(status_code=500, detail="Error reading template file")

def extract_json_from_bedrock_result(result: str) -> str:
    """Extract only the JSON part from Bedrock result"""
    try:
        # Find the JSON object in the result
        json_match = re.search(r'\{[^{]*"[^"]+"\s*:\s*\[[^\]]*\][^}]*\}', result)
        if not json_match:
            raise ValueError("No JSON found in Bedrock result")
        
        json_str = json_match.group(0)
        
        # Log the rest of the content
        other_content = result.replace(json_str, '').strip()
        logging.info(f"Additional Bedrock output: {other_content}")
        
        # Validate JSON
        json.loads(json_str)  # This will raise JSONDecodeError if invalid
        return json_str
        
    except Exception as e:
        logging.error(f"Error extracting JSON from Bedrock result: {e}")
        raise ValueError(f"Failed to process Bedrock result: {str(e)}")


def process_json_data(json_data):
    """Process JSON data to extract words and format them"""
    try:
        # Parse JSON if it's a string
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        
        # Ensure it's a list
        if not isinstance(json_data, list):
            raise ValueError("JSON data must be an array")
        
        # Extract only the "word" values
        words = [item.get("word") for item in json_data if item.get("word")]
        
        # Format as a string set
        formatted_str = "{" + ", ".join(f'"{word}"' for word in words) + "}"
        
        return words, formatted_str
    except Exception as e:
        logging.error(f"Error processing JSON data: {e}")
        raise ValueError(f"Invalid JSON format: {str(e)}")

async def generate_batch_variations(session, words_batch, system_prompt, model_name):
    """Generate variations for a batch of words"""
    try:
        # Format batch as input dict
        batch_dict = "{" + ", ".join(f'"{word}"' for word in words_batch) + "}"
        
        # Replace placeholder in system prompt
        batch_system_prompt = system_prompt.replace("{input_dict}", batch_dict)
        
        # Call Bedrock service
        bedrock_result = await call_bedrock(batch_dict, batch_system_prompt, session, model_name)
        
        # Extract JSON from result
        json_result = extract_json_from_bedrock_result(bedrock_result)
        
        return json.loads(json_result)
    except Exception as e:
        logging.error(f"Batch variation generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch variation generation failed: {str(e)}")

@app.post('/generate_variation')
async def generate_variation(request_data: dict):
    try:
        # Get JSON data from request
        json_data = request_data.get('json_data')
        if not json_data:
            raise HTTPException(status_code=400, detail="Missing JSON data")

        # Process JSON data to extract words
        words, formatted_input = process_json_data(json_data)
        logging.info(f"Formatted input: {formatted_input}")

        # Get the system prompt from llm_generate_dict.txt
        system_prompt = read_llm_generate_dict()
        logging.info(f"System prompt length: {len(system_prompt)}")

        # Get AWS session
        session, _ = get_temporary_credentials()
        
        # Call Bedrock service with Claude 3.5 Sonnet
        model_name = "claude-3-5-sonnet"

        # Batch processing: 2-3 words per batch to control token usage
        batch_size = 5
        all_variations = {}

        # Process words in batches
        for i in range(0, len(words), batch_size):
            words_batch = words[i:i+batch_size]
            batch_variations = await generate_batch_variations(session, words_batch, system_prompt, model_name)
            all_variations.update(batch_variations)

        # Combine variations into a single JSON
        final_json_result = json.dumps(all_variations)

        # Read template and replace placeholder
        template = read_template()
        final_result = template.replace("{generate_result}", final_json_result)

        return {
            'bedrock_result': final_result
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Variation generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Variation generation failed: {str(e)}")

@app.post('/login')
async def login(credentials: dict):
    username = credentials.get('username')
    password = credentials.get('password')
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username or password")
    
    if username != 'zxxm' or password != RANDOM_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"message": "Login successful"}

def read_llm_generate_dict():
    """Read the content of llm_generate_dict.txt"""
    try:
        with open(LLM_GENERATE_DICT_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                raise ValueError("System prompt file is empty")
            return content
    except Exception as e:
        logging.error(f"Error reading llm_generate_dict.txt: {e}")
        raise HTTPException(status_code=500, detail="Error reading system prompt file")

@app.get('/get_ec2_role')
async def fetch_ec2_role():
    try:
        logging.info("Received request to fetch EC2 role")
        role = get_ec2_role()
        _, credentials = get_temporary_credentials()
        region = get_aws_region()
        logging.info(f"Successfully fetched EC2 role and credentials for role: {role}")
        return {
            "role": role,
            "region": region,
            "accessKeyId": credentials['AccessKeyId'],
            "secretAccessKey": credentials['SecretAccessKey'],
            "sessionToken": credentials['Token']
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in fetch_ec2_role: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post('/upload_to_s3')
async def upload_to_s3(
    file: UploadFile = File(...),
    s3_path: str = Form(...),
):
    try:
        logging.info(f"Received file upload request: {file.filename} to {s3_path}")
        
        # Get AWS session
        session, _ = get_temporary_credentials()
        s3_client = session.client('s3')

        # Upload file
        try:
            file_content = await file.read()
            s3_url = urlparse(s3_path)
            
            if s3_url.scheme != 's3':
                raise HTTPException(status_code=400, detail="Invalid S3 path. Must start with 's3://'")
            
            bucket_name = s3_url.netloc
            object_key = s3_url.path.lstrip('/')
            
            if not bucket_name or not object_key:
                raise HTTPException(status_code=400, detail="Invalid S3 path format")

            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=file_content,
                ContentType=file.content_type
            )
            logging.info(f"Successfully uploaded file to S3: s3://{bucket_name}/{object_key}")
            
            return {
                "message": "File uploaded successfully",
                "s3_url": f"s3://{bucket_name}/{object_key}"
            }
        except Exception as e:
            logging.error(f"S3 upload error: {e}")
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Unexpected upload error: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")

@app.post('/transcribe')
async def handle_transcribe_audio(request_data: dict):
    try:
        logging.info("=== Transcribe Request Data ===")
        logging.info(f"Request data: {request_data}")
        
        # Get AWS session
        session, _ = get_temporary_credentials()

        # Extract required parameters
        s3_audio_url = request_data.get('s3_audio_url')
        system_prompt = request_data.get('system_prompt')
        model_name = request_data.get('model_name')

        # Log parameters
        logging.info(f"s3_audio_url: {s3_audio_url}")
        logging.info(f"system_prompt: {system_prompt}")
        logging.info(f"model_name: {model_name}")

        # Validate required parameters
        if not all([s3_audio_url, system_prompt, model_name]):
            missing_fields = []
            if not s3_audio_url: missing_fields.append("s3_audio_url")
            if not system_prompt: missing_fields.append("system_prompt")
            if not model_name: missing_fields.append("model_name")
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logging.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        # Call transcription service
        result = await transcribe_audio(session, s3_audio_url, system_prompt, model_name)
        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Transcription process failed")

@app.post('/bedrock')
async def bedrock_inference(request_data: dict):
    try:
        # Validate input
        transcript = request_data.get('transcript')
        system_prompt = request_data.get('system_prompt')
        model_name = request_data.get('model_name')

        if not all([transcript, system_prompt, model_name]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        if model_name not in SUPPORTED_MODELS:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {model_name}")

        logging.info(f"Received Bedrock inference request for model: {model_name}")

        # Get AWS session
        session, _ = get_temporary_credentials()
        
        # Call Bedrock service
        bedrock_result = await call_bedrock(transcript, system_prompt, session, model_name)

        return {
            'bedrock_result': bedrock_result
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Bedrock inference error: {e}")
        raise HTTPException(status_code=500, detail="Bedrock inference failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
