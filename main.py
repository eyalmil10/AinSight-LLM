import boto3, json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.invoke_model(
    #modelId="anthropic.claude-3-haiku-20240307-v1:0",
    modelId="meta.llama3-8b-instruct-v1:0",
    body=json.dumps({
        "messages": [
            {"role": "user", "content": "תסביר בקצרה מה זה Bedrock"}
        ],
        "max_tokens": 150
    })
)

print(json.loads(response["body"].read()))
