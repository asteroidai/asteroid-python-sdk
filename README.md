# Asteroid Python SDK
A Python SDK for interacting with the Asteroid platform. To successfully use Asteroid Python SDK, you need to have a running instance of the Asteroid server. [Book a demo]( https://calendly.com/founders-asteroid-hhaf/30min) with Asteroid founders to get started!


## Installation
```bash
pip install asteroid-sdk
```

## Quick Start
```python
from asteroid_sdk.wrappers.openai import asteroid_openai_client, asteroid_init
from asteroid_sdk.supervision.decorators import supervise
from asteroid_sdk.supervision.supervisors import llm_supervisor, human_supervisor
from openai import OpenAI

# Initialize the SDK
run_id = asteroid_init()

# Define your tools with supervisors
@supervise(supervision_functions=[[llm_supervisor(instructions="For flights above $1000, escalate."), human_supervisor()]])
def book_flight(departure_city: str, arrival_city: str, datetime: str):
    """Book a flight ticket."""
    return f"Flight booked from {departure_city} to {arrival_city} on {datetime}."

# Wrap your LLM client
client = OpenAI()
wrapped_client = asteroid_openai_client(client, run_id)

# Run your LLM
response = wrapped_client.chat.completions.create(
  model="gpt-4o",
  messages=[{"role": "user", "content": "Book a flight from SF to LA for tomorrow for $1100."}],
  tools=[book_flight]
)
# The response is supervised by Asteroid, check the web UI for the results and human review
```

## Documentation

For more information, please refer to the [Asteroid Documentation](https://docs.asteroid.ai/)! 

