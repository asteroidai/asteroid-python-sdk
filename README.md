### README.md

# Sentinel Python SDK
A Python SDK for interacting with the Sentinel platform.

## Installation
```bash
pip install sentinel-python-sdk
```
  
## Quick Start
```python
import sentinel
# Initialize the SDK
sentinel.init(api_key="your_api_key")
# Use your LLM client as usual
import openai
response = openai.ChatCompletion.create(
  model="gpt-3.5-turbo",
  messages=[{"role": "user", "content": "Hello, how are you?"}]
)
print(response)
```

# Development 

This SDK makes use of a generated client from the OpenAPI spec. To update the spec, run the following command from the root of the repo (assuming that the OpenAPI spec is in the ../sentinel/server directory):

```bash
openapi-python-client generate --path ../sentinel/server/openapi.yaml  --output-path sentinel/api/generated --overwrite
```
