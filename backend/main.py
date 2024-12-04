import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from urllib.parse import urlparse

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
        # Get AWS session
        session, _ = get_temporary_credentials()

        # Extract required parameters
        s3_audio_url = request_data.get('s3_audio_url')
        system_prompt = request_data.get('system_prompt')
        model_name = request_data.get('model_name')

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
