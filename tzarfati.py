# Use the native inference API to send a text message to Anthropic - Clause Sonnet 4.5

import boto3

import json
 
from botocore.exceptions import ClientError
 
# Create a Bedrock Runtime client in the AWS Region of your choice.

client = boto3.client("bedrock-runtime", region_name="eu-central-1")
 
 
# Set the model ID, e.g., claude-sonnet-4-5.

model_id = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
 
# Define the prompt for the model.

prompt = "Describe the purpose of a 'hello world' program in one line."
 
# Format the request payload using the model's native structure.

native_request = {

    "anthropic_version":"bedrock-2023-05-31",

    "max_tokens":50,

    "messages":[

        {

            "role":"user",

            "content":prompt

        }

    ]

}
 
# Convert the native request to JSON.

request = json.dumps(native_request)
 
try:

    # Invoke the model with the request.

    response = client.invoke_model(modelId=model_id, body=request)
 
except (ClientError, Exception) as e:

    print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")

    exit(1)
 
# Decode the response body.

model_response = json.loads(response["body"].read())
 
# Extract and print the response text.

response_text = model_response["content"][0]["text"]

print("---------------------------------------")

print("Finished Successfully")

print(f"Model output: \n{response_text}")

print("---------------------------------------")
 