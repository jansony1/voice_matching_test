import logging
import time
import json
import boto3
from fastapi import HTTPException
from .config import SUPPORTED_MODELS
from .logging_utils import log_execution_time



def generate_conversation(
    bedrock_client, 
    model_id, 
    system_prompts, 
    messages, 
    inference_config, 
    additional_model_request_fields=None
):
    """
    Sends messages to a model using the Bedrock Converse API.
    
    Parameters:
        bedrock_client: The Bedrock client used to interact with the API.
        model_id: The ID of the model to use.
        system_prompts: System prompts to pass to the model.
        messages: User messages for the conversation.
        inference_config: Configuration for model inference (e.g., temperature, max tokens).
        additional_model_request_fields: (Optional) Additional fields for specific models.
    """
    logging.info(f"Generating message with model {model_id}")

    try:
        start_time = time.time()

        # 动态构建请求参数
        if additional_model_request_fields:
            # 调用方式包含 additionalModelRequestFields
            response = bedrock_client.converse(
                modelId=model_id,
                messages=messages,
                system=system_prompts,
                inferenceConfig=inference_config,
                additionalModelRequestFields=additional_model_request_fields
            )
        else:
            # 调用方式不包含 additionalModelRequestFields
            response = bedrock_client.converse(
                modelId=model_id,
                messages=messages,
                system=system_prompts,
                inferenceConfig=inference_config
            )
        end_time = time.time()
        execution_time = end_time - start_time

        # Log execution time
        log_execution_time(model_id, execution_time)

        # Log token usage
        token_usage = response['usage']
        logging.info(f"Input tokens: {token_usage['inputTokens']}")
        logging.info(f"Output tokens: {token_usage['outputTokens']}")
        logging.info(f"Stop reason: {response['stopReason']}")
        logging.info(f"Execution time: {execution_time:.2f} seconds")

        return response

    except Exception as e:
        logging.error(f"Error in generate_conversation: {e}")
        raise

        

async def call_bedrock(transcript: str, system_prompt: str, session: boto3.Session, model_name: str):
    """
    Call Bedrock API with given transcript and system prompt
    """
    try:
        # Initialize Bedrock runtime client
        bedrock_runtime = session.client('bedrock-runtime')

        # Print SUPPORTED_MODELS content for debugging
        logging.info("=== SUPPORTED MODELS CONFIGURATION ===")
        logging.info(json.dumps(SUPPORTED_MODELS, indent=2))
        logging.info("=====================================")
        logging.info(f"Requested model name: {model_name}")

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
        additional_request_fields = inference_config.get("additionalModelRequestFields", {})

        # Generate conversation using the Converse API
        response = generate_conversation(
            bedrock_runtime,
            model_id,
            system_prompts,
            messages,
            inference_config，
            additional_request_fields
        )

        # Extract the model's response
        output_message = response['output']['message']
        result = output_message['content'][0]['text']
        logging.info(f"Bedrock {model_name} result: {result}")

        return result

    except Exception as e:
        logging.error(f"Error calling Bedrock API: {e}")
        raise HTTPException(status_code=500, detail=f"Bedrock API call failed: {str(e)}")
