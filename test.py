from openai import OpenAI
from sentinel.wrappers.openai import wrap_client

# Create OpenAI client
client = OpenAI()

# Wrap it with Sentinel logging and project registration
wrapped_client = wrap_client(client, project_name="my-awesome-project")

# Use it normally - project is already registered
response = wrapped_client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
