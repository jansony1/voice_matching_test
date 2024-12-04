import logging
import requests
import json
import boto3
from fastapi import HTTPException
from datetime import datetime, timezone
from dateutil import parser
from config import DEFAULT_AWS_REGION, METADATA_SERVICE_URL

def get_imdsv2_token():
    """
    Fetch IMDSv2 token for AWS instance metadata
    """
    try:
        logging.info("Attempting to fetch IMDSv2 token")
        token_response = requests.put(
            f"{METADATA_SERVICE_URL}/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=2
        )
        token_response.raise_for_status()
        logging.info("Successfully fetched IMDSv2 token")
        return token_response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching IMDSv2 token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch IMDSv2 token: {str(e)}")

def get_aws_region():
    """
    Retrieve AWS region from instance metadata
    """
    try:
        logging.info("Attempting to fetch AWS region from instance metadata")
        token = get_imdsv2_token()
        response = requests.get(
            f"{METADATA_SERVICE_URL}/meta-data/placement/region",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=2
        )
        response.raise_for_status()
        region = response.text
        logging.info(f"Successfully fetched AWS region: {region}")
        return region
    except Exception as e:
        logging.error(f"Error fetching AWS region: {e}")
        return DEFAULT_AWS_REGION

def get_instance_metadata(metadata_path):
    """
    Fetch specific instance metadata
    """
    token = get_imdsv2_token()
    try:
        logging.info(f"Attempting to fetch instance metadata: {metadata_path}")
        response = requests.get(
            f"{METADATA_SERVICE_URL}/meta-data/{metadata_path}",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=5
        )
        response.raise_for_status()
        logging.info(f"Successfully fetched instance metadata: {metadata_path}")
        return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching instance metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch instance metadata: {str(e)}")

def get_ec2_role():
    """
    Retrieve EC2 IAM role
    """
    try:
        logging.info("Attempting to fetch EC2 role")
        role = get_instance_metadata("iam/security-credentials/")
        if not role:
            raise HTTPException(status_code=500, detail="No IAM role found")
        logging.info(f"Successfully fetched EC2 role: {role}")
        return role
    except Exception as e:
        logging.error(f"Unexpected error fetching EC2 role: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching EC2 role: {str(e)}")

def get_temporary_credentials():
    """
    Retrieve temporary AWS credentials
    """
    session = None
    credentials = None
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
