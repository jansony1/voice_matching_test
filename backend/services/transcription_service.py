import logging
import uuid
import asyncio
import requests
from fastapi import HTTPException
from urllib.parse import urlparse
from config import SUPPORTED_MODELS
from bedrock_service import call_bedrock

async def transcribe_audio(session, s3_audio_url: str, system_prompt: str, model_name: str):
    """
    Transcribe audio from S3 and process with Bedrock
    """
    try:
        # Validate inputs
        if not all([s3_audio_url, system_prompt, model_name]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        if model_name not in SUPPORTED_MODELS:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {model_name}")

        logging.info(f"Received transcribe request for S3 audio file: {s3_audio_url} using model: {model_name}")

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
