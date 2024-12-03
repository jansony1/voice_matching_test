import logging
import os
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import boto3
import json
import uuid
import requests
import asyncio
from botocore.exceptions import ClientError
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone
from dateutil import parser
from urllib.parse import urlparse

# Define supported models and their configurations
SUPPORTED_MODELS = {
    "claude-3-haiku": {
        "id": "anthropic.claude-3-haiku-20240307-v1:0",
        "config": {
            "temperature": 0.5,
            "topP": 0.9,
            "maxTokens": 1000
        }
    },
    "claude-3-5-haiku": {
        "id": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "config": {
            "temperature": 0.5,
            "topP": 0.9,
            "maxTokens": 1000
        }
    }
}

# Configure logging
log_file = os.path.join(os.path.dirname(__file__), 'app.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

app = FastAPI(root_path="/api")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

# OAuth2 scheme for token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Global variables for EC2 role and credentials
ec2_role = None
session = None
credentials = None
aws_region = None

def get_aws_region():
    global aws_region
    if aws_region is None:
        try:
            logging.info("Attempting to fetch AWS region from instance metadata")
            token = get_imdsv2_token()
            response = requests.get(
                "http://169.254.169.254/latest/meta-data/placement/region",
                headers={"X-aws-ec2-metadata-token": token},
                timeout=2
            )
            response.raise_for_status()
            aws_region = response.text
            logging.info(f"Successfully fetched AWS region: {aws_region}")
        except Exception as e:
            logging.error(f"Error fetching AWS region: {e}")
            aws_region = "us-west-2"  # Default fallback
            logging.info(f"Using default region: {aws_region}")
    return aws_region

def get_imdsv2_token():
    try:
        logging.info("Attempting to fetch IMDSv2 token")
        token_response = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=2
        )
        token_response.raise_for_status()
        logging.info("Successfully fetched IMDSv2 token")
        return token_response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching IMDSv2 token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch IMDSv2 token: {str(e)}")

def get_instance_metadata(metadata_path):
    token = get_imdsv2_token()
    try:
        logging.info(f"Attempting to fetch instance metadata: {metadata_path}")
        response = requests.get(
            f"http://169.254.169.254/latest/meta-data/{metadata_path}",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=5
        )
        response.raise_for_status()
        logging.info(f"Successfully fetched instance metadata: {metadata_path}")
        return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching instance metadata: {e}")
        if isinstance(e, requests.Timeout):
            raise HTTPException(status_code=500, detail="Timeout while fetching instance metadata. Ensure the application is running on an EC2 instance.")
        elif isinstance(e, requests.ConnectionError):
            raise HTTPException(status_code=500, detail="Failed to connect to instance metadata service. Ensure the application is running on an EC2 instance.")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch instance metadata: {str(e)}")

def get_ec2_role():
    global ec2_role
    if ec2_role is None:
        try:
            logging.info("Attempting to fetch EC2 role")
            ec2_role = get_instance_metadata("iam/security-credentials/")
            if not ec2_role:
                raise HTTPException(status_code=500, detail="No IAM role found. Ensure the EC2 instance has an IAM role attached.")
            logging.info(f"Successfully fetched EC2 role: {ec2_role}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logging.error(f"Unexpected error fetching EC2 role: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error fetching EC2 role: {str(e)}")
    return ec2_role

def get_temporary_credentials():
    global session, credentials
    current_time = datetime.now(timezone.utc)
    needs_refresh = True

    if session is not None and credentials is not None and 'Expiration' in credentials:
        try:
            expiration = parser.parse(credentials['Expiration'])
            needs_refresh = expiration <= current_time
        except (ValueError, TypeError) as e:
            logging.error(f"Error parsing expiration time: {e}")
            needs_refresh = True

    if needs_refresh:
        role = get_ec2_role()
        try:
            logging.info(f"Attempting to fetch temporary credentials for role: {role}")
            creds_json = get_instance_metadata(f"iam/security-credentials/{role}")
            credentials = json.loads(creds_json)
            session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['Token']
            )
            logging.info("Successfully fetched temporary credentials")
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing temporary credentials: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse temporary credentials")
        except Exception as e:
            logging.error(f"Error fetching temporary credentials: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch temporary credentials: {str(e)}")
    return session, credentials

def generate_conversation(bedrock_client, model_id, system_prompts, messages, inference_config):
    """
    Sends messages to a model using the Bedrock Converse API.
    """
    logging.info(f"Generating message with model {model_id}")

    try:
        # Send the message using the converse API
        response = bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            system=system_prompts,
            inferenceConfig=inference_config
        )

        # Log token usage
        token_usage = response['usage']
        logging.info(f"Input tokens: {token_usage['inputTokens']}")
        logging.info(f"Output tokens: {token_usage['outputTokens']}")
        logging.info(f"Total tokens: {token_usage['totalTokens']}")
        logging.info(f"Stop reason: {response['stopReason']}")

        return response

    except Exception as e:
        logging.error(f"Error in generate_conversation: {e}")
        raise

async def call_bedrock(transcript: str, system_prompt: str, session: boto3.Session, model_name: str):
    try:
        # Initialize Bedrock runtime client
        bedrock_runtime = session.client('bedrock-runtime')

        if model_name not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")

        model_info = SUPPORTED_MODELS[model_name]
        model_id = model_info["id"]
        inference_config = model_info["config"]

        # Prepare system prompts and messages
        system_prompts = [{"text": system_prompt}]
        messages = [{
            "role": "user",
            "content": [{"text": transcript}]
        }]

        # Generate conversation using the Converse API
        response = generate_conversation(
            bedrock_runtime,
            model_id,
            system_prompts,
            messages,
            inference_config
        )

        # Extract the model's response
        output_message = response['output']['message']
        result = output_message['content'][0]['text']
        logging.info(f"Bedrock {model_name} result: {result}")

        return result

    except Exception as e:
        logging.error(f"Error calling Bedrock API: {e}")
        raise HTTPException(status_code=500, detail=f"Bedrock API call failed: {str(e)}")

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
        
        # Parse S3 path
        s3_url = urlparse(s3_path)
        if s3_url.scheme != 's3':
            raise HTTPException(status_code=400, detail="Invalid S3 path. Must start with 's3://'")
        
        bucket_name = s3_url.netloc
        # Remove leading slash from key
        object_key = s3_url.path.lstrip('/')
        
        if not bucket_name or not object_key:
            raise HTTPException(status_code=400, detail="Invalid S3 path format. Must be 's3://bucket-name/path/to/file'")

        # Get AWS session
        session, _ = get_temporary_credentials()
        s3_client = session.client('s3')

        # Upload file
        try:
            file_content = await file.read()
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
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logging.error(f"S3 upload error: {error_code} - {error_message}")
            raise HTTPException(
                status_code=500,
                detail=f"S3 upload failed: {error_code} - {error_message}"
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in upload_to_s3: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error during file upload: {str(e)}")

@app.post('/transcribe')
async def transcribe_audio(request_data: dict):
    try:
        # Extract data from request
        s3_audio_url = request_data.get('s3_audio_url')
        system_prompt = request_data.get('system_prompt')
        model_name = request_data.get('model_name')

        if not all([s3_audio_url, system_prompt, model_name]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        if model_name not in SUPPORTED_MODELS:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {model_name}")

        logging.info(f"Received transcribe request for S3 audio file: {s3_audio_url} using model: {model_name}")

        # Get AWS session using EC2 instance role
        session, _ = get_temporary_credentials()

        # Initialize Transcribe client
        transcribe = session.client('transcribe')

        # Generate unique job name
        job_name = f'transcribe-job-{str(uuid.uuid4())}'

        # Start transcription job
        try:
            transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': s3_audio_url},
                MediaFormat='mp3',  # Adjust based on input format
                LanguageCode='en-US'
            )
            logging.info(f"Started transcription job: {job_name}")
        except Exception as e:
            logging.error(f"Error starting transcription job: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription job failed: {str(e)}")

        # Wait for transcription completion
        while True:
            status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            await asyncio.sleep(1)

        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'FAILED':
            logging.error(f"Transcription job failed: {status['TranscriptionJob']['Failure']['FailureReason']}")
            raise HTTPException(status_code=500, detail="Transcription job failed")

        # Get transcription result
        transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        try:
            transcript_response = requests.get(transcript_uri)
            transcript_response.raise_for_status()
            transcript_text = transcript_response.json()['results']['transcripts'][0]['transcript']
            logging.info(f"Transcription result: {transcript_text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error retrieving transcription result: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve transcription result: {str(e)}")
        except (ValueError, KeyError) as e:
            logging.error(f"Invalid transcription result format: {e}")
            raise HTTPException(status_code=500, detail=f"Invalid transcription result format: {str(e)}")

        # Call Bedrock Claude with the specified model
        bedrock_result = await call_bedrock(transcript_text, system_prompt, session, model_name)

        # Clean up transcription job
        try:
            transcribe.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception as e:
            logging.warning(f"Failed to delete transcription job: {str(e)}")

        return {
            'transcript': transcript_text,
            'bedrock_claude_result': bedrock_result
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/bedrock')
async def bedrock_inference(request_data: dict):
    try:
        transcript = request_data.get('transcript')
        system_prompt = request_data.get('system_prompt')
        model_name = request_data.get('model_name')

        if not all([transcript, system_prompt, model_name]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        if model_name not in SUPPORTED_MODELS:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {model_name}")

        logging.info(f"Received Bedrock inference request for model: {model_name}")

        session, _ = get_temporary_credentials()
        bedrock_result = await call_bedrock(transcript, system_prompt, session, model_name)

        return {
            'bedrock_result': bedrock_result
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
