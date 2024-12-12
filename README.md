### README.md

# Asteroid Python SDK
A Python SDK for interacting with the Asteroid platform.

## Installation
From the package:

```bash
pip install asteroid-sdk
```

## Quick Start
```python
import asteroid
# Initialize the SDK
asteroid.init(api_key="your_api_key")
# Use your LLM client as usual
import openai
response = openai.ChatCompletion.create(
  model="gpt-3.5-turbo",
  messages=[{"role": "user", "content": "Hello, how are you?"}]
)
print(response)
```

# Development 

This SDK makes use of a generated client from the OpenAPI spec. To update the spec, run the following command from the root of the repo (assuming that the OpenAPI spec is in the ../asteroid/server directory):

First, install the openapi-python-client package https://github.com/openapi-generators/openapi-python-client
```bash
pip install openapi-python-client
```

Then, generate the client:
```bash
openapi-python-client generate --path ../asteroid/server/openapi.yaml  --output-path src/asteroid/api/generated --overwrite
```
