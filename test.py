from sentinel.supervision.decorators import supervise
# Define a supervisor
def my_supervisor():
    """Human supervisor for reviewing actions."""
    def human_supervisor(action, context):
        # Supervisor implementation
        print(f"Supervisor received action: {action}")
        pass
    return human_supervisor

# Use the decorator
@supervise(supervision_functions=[[my_supervisor()]])
def book_flight(departure_city: str, arrival_city: str, datetime: str, maximum_price: float):
    """Book a flight ticket."""
    return f"Flight booked from {departure_city} to {arrival_city} on {datetime}."

@supervise(supervision_functions=[[my_supervisor()]])
def get_weather(location: str, unit: str):
    """Get the weather in a city."""
    return f"The weather in {location} is {unit}."

def your_supervisor():
    """Your supervisor."""
    def supervisor1(action, context):
        # Supervisor implementation
        print(f"Supervisor received action: {action}")
        pass
    return supervisor1

@supervise(supervision_functions=[[your_supervisor(), my_supervisor()]], ignored_attributes=["maximum_price"])
def book_hotel(location: str, checkin: str, checkout: str, maximum_price: float):
    """Book a hotel."""
    return f"Hotel booked in {location} from {checkin} to {checkout}."

# When you wrap the client, all supervised functions will be registered
from openai import OpenAI
from sentinel.wrappers.openai import sentinel_openai_client, sentinel_init, sentinel_end

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
    }, 
    {
        "type": "function",
        "function": {
            "name": "book_flight",
            "parameters": {
                "type": "object",
                "properties": {
                    "departure_city": {"type": "string"},
                    "arrival_city": {"type": "string"},
                    "datetime": {"type": "string"},
                    "maximum_price": {"type": "number"},
                },
            },
        },
    }, 
    {
        "type": "function",
        "function": {
            "name": "book_hotel",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "checkin": {"type": "string"},
                    "checkout": {"type": "string"},
                    "maximum_price": {"type": "number"},
                },
            },
        },
    },
]


client = OpenAI()

for i in range(1):
    run_id = sentinel_init(
        project_name="my-project", 
        task_name="my-task", 
        run_name="my-run"
    )
    wrapped_client = sentinel_openai_client(client, run_id)

    response = wrapped_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"content":[{"text":"What's the weather in Tokyo please use the get_weather tool?","type":"text"}],"role":"user"}],
        tools=tools,
        tool_choice="auto",
        temperature=1.5,
        n=5
    )

    for choice in response.choices:
        print(choice.message.tool_calls)
        # print(choice.message.tool_calls)
    # print(response)




# Bring your favourite LLM client
client = OpenAI()

# Initialize Sentinel
run_id = sentinel_init()

# Wrap your client
client = sentinel_openai_client(client, run_id)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"content":[{"text":"What's the weather in Tokyo?","type":"text"}],"role":"user"}],
)


