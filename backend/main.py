import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
import json
import uuid
import requests
import asyncio

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

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

@app.options("/validate_credentials")
def validate_credentials_options():
    return {"message": "OPTIONS request handled"}

@app.post('/validate_credentials')
def validate_credentials(request_data: dict):
    try:
        aws_access_key_id = request_data.get('aws_access_key_id')
        aws_secret_access_key = request_data.get('aws_secret_access_key')
        aws_region = request_data.get('aws_region', 'us-west-2')

        logging.info(f"Received validate_credentials request with AWS credentials: {aws_access_key_id}, {aws_region}")

        if not all([aws_access_key_id, aws_secret_access_key]):
            logging.error("Missing required fields")
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Configure AWS session
        logging.info("Configuring AWS session")
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

        # Try to validate credentials using STS
        logging.info("Validating AWS credentials")
        sts = session.client('sts')
        try:
            sts.get_caller_identity()
            logging.info("Credentials validated successfully")
            return {"message": "Credentials are valid"}
        except Exception as e:
            logging.error(f"Error validating credentials: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logging.error(f"Error validating credentials: {e}")
        raise HTTPException(status_code=400, detail=str(e))

async def call_bedrock(transcript: str, system_prompt: str, aws_credentials: dict):
    try:
        # Configure AWS session
        session = boto3.Session(
            aws_access_key_id=aws_credentials['aws_access_key_id'],
            aws_secret_access_key=aws_credentials['aws_secret_access_key'],
            region_name=aws_credentials['aws_region']
        )

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
        aws_access_key_id = request_data.get('aws_access_key_id')
        aws_secret_access_key = request_data.get('aws_secret_access_key')
        aws_region = request_data.get('aws_region', 'us-west-2')

        if not all([s3_audio_url, system_prompt, aws_access_key_id, aws_secret_access_key]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        logging.info(f"Received transcribe request for S3 audio file: {s3_audio_url}")

        # Configure AWS session
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

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
        aws_credentials = {
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key,
            'aws_region': aws_region
        }
        bedrock_result = await call_bedrock(transcript_text, system_prompt, aws_credentials)

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
        aws_access_key_id = request_data.get('aws_access_key_id')
        aws_secret_access_key = request_data.get('aws_secret_access_key')
        aws_region = request_data.get('aws_region', 'us-west-2')

        if not all([transcript, system_prompt, aws_access_key_id, aws_secret_access_key]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        logging.info(f"Received Bedrock inference request")

        aws_credentials = {
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key,
            'aws_region': aws_region
        }
        bedrock_result = await call_bedrock(transcript, system_prompt, aws_credentials)

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
