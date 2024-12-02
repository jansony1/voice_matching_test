import logging
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import boto3
import json
import uuid
import requests
import asyncio
from botocore.exceptions import ClientError
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone

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
    if session is None or credentials is None or credentials.get('Expiration', 0) <= datetime.now(timezone.utc):
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

@app.get('/get_ec2_role')
async def fetch_ec2_role():
    try:
        logging.info("Received request to fetch EC2 role")
        role = get_ec2_role()
        _, credentials = get_temporary_credentials()
        logging.info(f"Successfully fetched EC2 role and credentials for role: {role}")
        return {"role": role, "token": credentials['Token']}
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in fetch_ec2_role: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

async def call_bedrock(transcript: str, system_prompt: str, session: boto3.Session):
    try:
        # Initialize Bedrock client
        bedrock_runtime = session.client('bedrock-runtime')

        # Prepare prompt for Bedrock Claude
        claude_prompt = f"{system_prompt}\n\nHuman: {transcript}\n\nAssistant:"

        # Call Bedrock Claude
        bedrock_response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-v2",
            body=json.dumps({
                "prompt": claude_prompt,
                "max_tokens_to_sample": 2000,
                "temperature": 0.7,
            })
        )
        bedrock_response_body = json.loads(bedrock_response['body'].read())
        bedrock_result = bedrock_response_body.get('completion', '')
        logging.info(f"Bedrock Claude result: {bedrock_result}")

        return bedrock_result

    except Exception as e:
        logging.error(f"Error calling Bedrock API: {e}")
        raise HTTPException(status_code=500, detail=f"Bedrock API call failed: {str(e)}")

@app.post('/transcribe')
async def transcribe_audio(request_data: dict):
    try:
        # Extract data from request
        s3_audio_url = request_data.get('s3_audio_url')
        system_prompt = request_data.get('system_prompt')

        if not all([s3_audio_url, system_prompt]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        logging.info(f"Received transcribe request for S3 audio file: {s3_audio_url}")

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

        # Call Bedrock Claude
        bedrock_result = await call_bedrock(transcript_text, system_prompt, session)

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

        if not all([transcript, system_prompt]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        logging.info(f"Received Bedrock inference request")

        session, _ = get_temporary_credentials()
        bedrock_result = await call_bedrock(transcript, system_prompt, session)

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
