import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import boto3
import json
import uuid
import requests
from typing import Dict
import asyncio
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from amazon_transcribe.auth import StaticCredentialResolver

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

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# Maximum audio chunk size for Amazon Transcribe Streaming SDK
MAX_CHUNK_SIZE = 4096  # 4 KB

# Timeout for Amazon Transcribe Streaming SDK (in seconds)
TRANSCRIBE_TIMEOUT = 30

class WebSocketTranscriptHandler(TranscriptResultStreamHandler):
    def __init__(self, websocket: WebSocket, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket = websocket
        self.partial_transcripts = []

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # 这里是我们接收和处理Amazon Transcribe返回结果的地方
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:
                if result.is_partial:
                    self.partial_transcripts.append(alt.transcript)
                    log_message = f"Partial transcript: {alt.transcript}"
                    logging.debug(log_message)
                    print(log_message)  # 打印到终端
                    await self.websocket.send_text(alt.transcript)
                else:
                    final_transcript = alt.transcript
                    log_message = f"Final transcript: {final_transcript}"
                    logging.info(log_message)
                    print(log_message)  # 打印到终端
                    complete_transcript = ''.join(self.partial_transcripts) + final_transcript
                    await self.websocket.send_text(complete_transcript)
                    self.partial_transcripts.clear()
                    logging.info("Transcription completed")
                    print("Transcription completed")  # 打印到终端

# AWS Credentials dependency
async def get_aws_credentials(websocket: WebSocket):
    try:
        credentials = await websocket.receive_json()
        aws_access_key_id = credentials.get('aws_access_key_id')
        aws_secret_access_key = credentials.get('aws_secret_access_key')
        aws_region = credentials.get('aws_region', 'us-west-2')

        if not all([aws_access_key_id, aws_secret_access_key]):
            await websocket.close(code=1008)  # Policy Violation
            raise ValueError("Missing required AWS credentials")

        return aws_access_key_id, aws_secret_access_key, aws_region
    except Exception as e:
        logging.error(f"Error receiving AWS credentials: {e}")
        await websocket.close(code=1008)  # Policy Violation
        raise

async def keep_connection_alive(stream):
    while True:
        try:
            await asyncio.sleep(5)  # Send an empty chunk every 5 seconds
            await stream.input_stream.send_audio_event(audio_chunk=b'\x00' * MAX_CHUNK_SIZE)
            logging.debug("Sent keep-alive audio chunk")
        except Exception as e:
            logging.error(f"Error in keep-alive mechanism: {e}")
            break

async def process_audio_stream(websocket: WebSocket, stream, client_id: str):
    audio_buffer = bytearray()
    last_chunk_timestamp = None

    try:
        while True:
            try:
                audio_chunk = await websocket.receive_bytes()
                audio_buffer.extend(audio_chunk)
                logging.debug(f"Received audio chunk of size {len(audio_chunk)} bytes for client {client_id}")
                last_chunk_timestamp = asyncio.get_running_loop().time()

                while len(audio_buffer) >= MAX_CHUNK_SIZE:
                    chunk = audio_buffer[:MAX_CHUNK_SIZE]
                    audio_buffer = audio_buffer[MAX_CHUNK_SIZE:]
                    logging.debug(f"Sending audio chunk of size {len(chunk)} bytes for client {client_id}")
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)

            except WebSocketDisconnect:
                logging.info(f"WebSocket disconnected for client {client_id}")
                break

            # Check for timeout
            current_time = asyncio.get_running_loop().time()
            if last_chunk_timestamp is not None and current_time - last_chunk_timestamp > TRANSCRIBE_TIMEOUT:
                logging.warning(f"Transcription timed out for client {client_id}")
                break

        # Send remaining audio data
        if audio_buffer:
            logging.debug(f"Sending remaining audio chunk of size {len(audio_buffer)} bytes for client {client_id}")
            await stream.input_stream.send_audio_event(audio_chunk=audio_buffer)

        await stream.input_stream.end_stream()

    except Exception as e:
        logging.error(f"Error in process_audio_stream for {client_id}: {e}")
        await stream.input_stream.end_stream()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    logging.info(f"WebSocket connection established for client {client_id}")
    keep_alive_task = None
    try:
        # Get AWS credentials
        aws_access_key_id, aws_secret_access_key, aws_region = await get_aws_credentials(websocket)

        # Set up Amazon Transcribe Streaming SDK with static credentials
        credential_resolver = StaticCredentialResolver(
            access_key_id=aws_access_key_id,
            secret_access_key=aws_secret_access_key
        )
        transcribe_client = TranscribeStreamingClient(
            region=aws_region,
            credential_resolver=credential_resolver
        )

        stream = await transcribe_client.start_stream_transcription(
            language_code='en-US',
            media_sample_rate_hz=16000,
            media_encoding='pcm'
        )

        # Set up transcript handler
        handler = WebSocketTranscriptHandler(websocket, stream.output_stream)

        # Start keep-alive task
        keep_alive_task = asyncio.create_task(keep_connection_alive(stream))

        # Process audio stream and handle events concurrently
        await asyncio.gather(
            process_audio_stream(websocket, stream, client_id),
            handler.handle_events()
        )

    except Exception as e:
        logging.error(f"WebSocket error for client {client_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        if keep_alive_task is not None:
            keep_alive_task.cancel()
        active_connections.pop(client_id, None)
        logging.info(f"WebSocket connection closed for client {client_id}")

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

        # Initialize Transcribe and Bedrock clients
        transcribe = session.client('transcribe')
        bedrock_runtime = session.client('bedrock-runtime')

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

        # Prepare prompt for Bedrock Claude
        claude_prompt = f"{system_prompt}\n\nHuman: {transcript_text}\n\nAssistant:"

        # Call Bedrock Claude
        try:
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
        except Exception as e:
            logging.error(f"Error calling Bedrock API: {e}")
            raise HTTPException(status_code=500, detail=f"Bedrock API call failed: {str(e)}")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# 其余代码保持不变
