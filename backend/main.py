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
        token_response = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=2
        )
        token_response.raise_for_status()
        return token_response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching IMDSv2 token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch IMDSv2 token: {str(e)}")

def get_instance_metadata(metadata_path):
    token = get_imdsv2_token()
    try:
        response = requests.get(
            f"http://169.254.169.254/latest/meta-data/{metadata_path}",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=2
        )
        response.raise_for_status()
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
            ec2_role = get_instance_metadata("iam/security-credentials/")
            if not ec2_role:
                raise HTTPException(status_code=500, detail="No IAM role found. Ensure the EC2 instance has an IAM role attached.")
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
            creds_json = get_instance_metadata(f"iam/security-credentials/{role}")
            credentials = json.loads(creds_json)
            session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['Token']
            )
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
        role = get_ec2_role()
        _, credentials = get_temporary_credentials()
        return {"role": role, "token": credentials['Token']}
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in fetch_ec2_role: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# ... (rest of the code remains unchanged)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
