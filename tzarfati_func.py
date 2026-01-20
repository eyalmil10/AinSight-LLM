import boto3
import json
from botocore.exceptions import ClientError


def call_claude_sonnet(
    prompt: str,
    region: str = "eu-central-1",
    model_id: str = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    max_tokens: int = 50,
) -> str:
    """
    Send a prompt to Anthropic Claude Sonnet via AWS Bedrock and return the text response.
    """
    client = boto3.client("bedrock-runtime", region_name=region)

    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(native_request)
        )
    except (ClientError, Exception) as e:
        raise RuntimeError(f"Can't invoke '{model_id}': {e}")

    model_response = json.loads(response["body"].read())
    return model_response["content"][0]["text"]
