import json
import os

os.environ["SENTINEL_API_URL"] = "http://localhost:8080/api/v1"

from sentinel.supervision.decorators import supervise
from sentinel.supervision.config import SupervisionDecision, SupervisionDecisionType
# Define a supervisor
def my_supervisor():
    """Supervisor for reviewing actions."""
    def supervisor1(action, supervision_context, **kwargs):
        # Supervisor implementation
        print(f"Supervisor received action: {action}")
        return SupervisionDecision(decision=SupervisionDecisionType.APPROVE)
    return supervisor1

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
    def supervisor2(action, supervision_context, **kwargs):
        # Supervisor implementation
        print(f"Supervisor received action: {action}")
        return SupervisionDecision(decision=SupervisionDecisionType.ESCALATE)
    return supervisor2

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

run_id = sentinel_init(
    project_name="my-project", 
    task_name="my-task", 
    run_name="my-run"
)
wrapped_client = sentinel_openai_client(client, run_id)

# Initialize conversation history
messages = []


# Run 5 interactions
for i in range(5):
    # Get user input
    user_input = input(f"\nEnter message {i+1}/5: ")
    
    # Add user message to history
    messages.append({"role": "user", "content": user_input})
    
    # Make API call
    response = wrapped_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=1.5,
        n=1
    )
    
    assistant_message = response.choices[0].message
    
    # Add assistant's response to conversation history
    messages.append({"role": "assistant", "content": assistant_message.content, "tool_calls": assistant_message.tool_calls})
    
    # If there are tool calls, execute them and add their results to the conversation
    if assistant_message.tool_calls:
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Execute the function
            if function_name == "get_weather":
                result = get_weather(**function_args)
            elif function_name == "book_flight":
                result = book_flight(**function_args)
            elif function_name == "book_hotel":
                result = book_hotel(**function_args)
            
            # Add the function response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })

sentinel_end(run_id)
