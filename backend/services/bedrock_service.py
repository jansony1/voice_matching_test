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
    additional_model_request_fields=None,
    performanceConfig=None):
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

        # 构建基本请求参数
        request_params = {
            'modelId': model_id,
            'messages': messages,
            'system': system_prompts,
            'inferenceConfig': inference_config
        }

        # 如果有额外的请求字段，添加到请求参数中
        if additional_model_request_fields:
            request_params['additionalModelRequestFields'] = additional_model_request_fields

        if performanceConfig:
            request_params['performanceConfig'] = performanceConfig


        # 执行单次调用
        response = bedrock_client.converse(**request_params)

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
        logging.error(f"Error generating conversation: {e}")
        raise

async def call_bedrock(transcript: str, system_prompt: str, session: boto3.Session, model_name: str):
    """
    Call Bedrock API with given transcript and system prompt
    """
    try:
        # Initialize Bedrock runtime client
        bedrock_runtime = session.client('bedrock-runtime')

        # Print SUPPORTED_MODELS for debugging
        logging.info("=== SUPPORTED_MODELS Content ===")
        logging.info(f"Type of SUPPORTED_MODELS: {type(SUPPORTED_MODELS)}")
        logging.info(f"Content of SUPPORTED_MODELS: {json.dumps(SUPPORTED_MODELS, indent=2)}")
        logging.info("==============================")

        if model_name not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")

        model_info = SUPPORTED_MODELS[model_name]
        model_id = model_info["id"]
        inference_config = model_info["config"]
        additional_request_fields = inference_config.pop("additionalModelRequestFields", None)
        performanceConfig = inference_config.pop("performanceConfig", None)

        # Extract dictionary from system_prompt
        start_index = system_prompt.find("<dictionary>")
        end_index = system_prompt.find("</dictionary>") + len("</dictionary>")
        dictionary_data = system_prompt[start_index:end_index]

        user_input = dictionary_data+ "<text>" + transcript + "</text>"
        # Remove dictionary part from system_prompt
        new_system_prompt = system_prompt[:start_index] + system_prompt[end_index:]

        # Prepare system prompts and messages
        system_prompts = [{"text": new_system_prompt}]
        messages = [{
            "role": "user",
            "content": [{"text": user_input}]
        }]

        # Generate conversation using the Converse API
        response = generate_conversation(
            bedrock_runtime,
            model_id,
            system_prompts,
            messages,
            inference_config,
            additional_request_fields,
            performanceConfig
        )

        # Extract the model's response
        output_message = response['output']['message']
        result = output_message['content'][0]['text']
        logging.info(f"Bedrock {model_name} result: {result}")

        return result

    except Exception as e:
        logging.error(f"Error calling Bedrock API: {e}")
        raise HTTPException(status_code=500, detail=f"Bedrock API call failed: {str(e)}")
