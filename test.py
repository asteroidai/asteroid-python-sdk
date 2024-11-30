from sentinel.supervision.registry import supervise

# Define a supervisor
def my_supervisor():
    """Human supervisor for reviewing actions."""
    def supervisor(action, context):
        # Supervisor implementation
        print(f"Supervisor received action: {action}")
        pass
    return supervisor

# Use the decorator
@supervise(supervision_functions=[[my_supervisor()]])
def book_flight(departure_city: str, arrival_city: str, datetime: str, maximum_price: float):
    """Book a flight ticket."""
    return f"Flight booked from {departure_city} to {arrival_city} on {datetime}."

# When you wrap the client, all supervised functions will be registered
from openai import OpenAI
from sentinel.wrappers.openai import wrap_client

client = OpenAI()
wrapped_client = wrap_client(client, project_name="my-project")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "unit": {"type": "string", "enum": ["c", "f"]},
                },
                "required": ["location", "unit"],
                "additionalProperties": False,
            },
        },
    }
]

response = wrapped_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"content":[{"text":"What's the weather in Tokyo?","type":"text"}],"role":"user"}],
    tools=tools,
    tool_choice="auto",
    temperature=1.7,
    n=5
)

for choice in response.choices:
    print(choice.message.content)
    # print(choice.message.tool_calls)
# print(response)
