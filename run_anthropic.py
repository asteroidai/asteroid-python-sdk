import json
import os
from typing import Any, List

from anthropic import Anthropic
from anthropic.types import ToolChoiceParam, ToolChoiceAutoParam, ToolParam, ToolUseBlock, TextBlock

from asteroid_sdk.wrappers.anthropic import asteroid_anthropic_client

os.environ["ASTEROID_API_URL"] = "http://localhost:8080/api/v1"

from asteroid_sdk.supervision.decorators import supervise
from asteroid_sdk.supervision.config import SupervisionDecision, SupervisionDecisionType, ExecutionMode, RejectionPolicy, MultiSupervisorResolution
from asteroid_sdk.supervision.supervisors import human_supervisor, openai_llm_supervisor, tool_supervisor_decorator, chat_supervisor_decorator

from asteroid_sdk.registration.initialise_project import asteroid_init, asteroid_end


@tool_supervisor_decorator(strategy="reject") #TODO: Rethink the decorator design, it can't be configured with parameters in this way
def supervisor1(
    tool_call: dict,
    config_kwargs: dict[str, Any],
    **kwargs
) -> SupervisionDecision:
    # Supervisor implementation using configuration parameters
    print(f"Supervisor received tool_call: {tool_call}")
    strategy = config_kwargs.get("strategy","")
    if strategy == "allow_all":
        return SupervisionDecision(decision=SupervisionDecisionType.APPROVE)
    else:
        return SupervisionDecision(decision=SupervisionDecisionType.REJECT)

# Use the decorator
@supervise(supervision_functions=[[openai_llm_supervisor(instructions="Always escalate"), human_supervisor()]], ignored_attributes=["maximum_price"])
def book_flight(departure_city: str, arrival_city: str, datetime: str, maximum_price: float):
    """Book a flight ticket."""
    return f"Flight booked from {departure_city} to {arrival_city} on {datetime}."

@supervise(supervision_functions=[[supervisor1]])
def get_weather(location: str, unit: str):
    """Get the weather in a city."""
    return f"The weather in {location} is {unit}."

@tool_supervisor_decorator(strategy="reject")
def supervisor2(tool_call, supervision_context, **kwargs):
    # Supervisor implementation
    print(f"Supervisor received tool_call: {tool_call}")
    return SupervisionDecision(decision=SupervisionDecisionType.ESCALATE)

@supervise(supervision_functions=[[supervisor2, supervisor1]], ignored_attributes=["maximum_price"])
def book_hotel(location: str, checkin: str, checkout: str, maximum_price: float):
    """Book a hotel."""
    return f"Hotel booked in {location} from {checkin} to {checkout}."


tools: list[ToolParam] = [
    {
        "name": "get_weather",
        "description": "Get the weather for a specific location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "unit": {"type": "string", "enum": ["c", "f"]},
            },
            "required": ["location", "unit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "book_flight",
        "description": "Book a flight ticket",
        "input_schema": {
            "type": "object",
            "properties": {
                "departure_city": {"type": "string"},
                "arrival_city": {"type": "string"},
                "datetime": {"type": "string"},
                "maximum_price": {"type": "number"},
            },
            "required": ["departure_city", "arrival_city", "datetime", "maximum_price"],
            "additionalProperties": False,
        },
    },
    {
        "name": "book_hotel",
        "description": "Book a hotel",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "checkin": {"type": "string"},
                "checkout": {"type": "string"},
                "maximum_price": {"type": "number"},
            },
            "required": ["location", "checkin", "checkout", "maximum_price"],
            "additionalProperties": False,
        },
    },
]

client = Anthropic()

EXECUTION_SETTINGS = {
    "execution_mode": ExecutionMode.SUPERVISION, # can be "monitoring" or "supervision", monitoring is async and supervision is sync by default
    "allow_tool_modifications": True, # allow the tool to be modified by the supervisor
    "rejection_policy": RejectionPolicy.RESAMPLE_WITH_FEEDBACK, # policy to use when the supervisor rejects the tool call
    "n_resamples": 1, # number of resamples to use when the supervisor rejects the tool call
    "multi_supervisor_resolution": MultiSupervisorResolution.ALL_MUST_APPROVE, # resolution strategy when multiple supervisors are running in parallel
    "remove_feedback_from_context": True, # remove the feedback from the context
}

for i in range(1):
    run_id = asteroid_init(
        project_name="my-project",
        task_name="my-task",
        run_name="my-run",
        execution_settings=EXECUTION_SETTINGS
    )
    # When you wrap the client, all supervised functions will be registered
    wrapped_client = asteroid_anthropic_client(client, run_id, EXECUTION_SETTINGS["execution_mode"])

# Initialize conversation history
messages = []

# Run 5 interactions
for i in range(5):
    # Get user input
    user_input = input(f"\nEnter message {i+1}/5: ")

    # Add user message to history
    messages.append({"role": "user", "content": user_input})

    response = wrapped_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=messages,
        tools=tools,
        tool_choice=ToolChoiceAutoParam(type="auto", disable_parallel_tool_use=True),
    )
    # Make API call
    assistant_message = response.content

    message_text: str|None = None
    tool_calls: List[ToolUseBlock]|None = None
    for message in assistant_message:
        if isinstance(message, ToolUseBlock):
            # We only allow 1 tool call for now
            tool_calls = [message]
        elif isinstance(message, TextBlock):
            message_text = message.text

    # Add assistant's response to conversation history
    messages.append({"role": "assistant", "content": message_text})

    if message:
        print(f"Assistant: {message_text}")

    # If there are tool calls, execute them and add their results to the conversation
    if tool_calls:
        for tool_call in tool_calls:
            function_name = tool_call.name
            function_args = tool_call.input

            # Execute the function
            print(f"Executing function: {function_name} with args: {function_args}")

            if function_name == "get_weather":
                result = get_weather(**function_args)
            elif function_name == "book_flight":
                result = book_flight(**function_args)
            elif function_name == "book_hotel":
                result = book_hotel(**function_args)

            print(f"Function result: {result}")
            # Add the function response to messages

asteroid_end(run_id)



# # Example chat supervisor that checks if 'Tokyo' is mentioned in the last message
# @chat_supervisor_decorator(strategy="reject")
# def chat_supervisor_1(message: dict, supervision_context, **kwargs) -> SupervisionDecision:
#     """
#     Supervisor that rejects any message mentioning 'Tokyo' in the last user message.
#     """
#     last_message = message.get('content', '')
#     if 'Tokyo' in last_message:
#         return SupervisionDecision(
#             decision=SupervisionDecisionType.REJECT,
#             explanation="The message mentions 'Tokyo', which is not allowed."
#         )
#     return SupervisionDecision(
#         decision=SupervisionDecisionType.APPROVE,
#         explanation="The message is approved."
#     )

# @chat_supervisor_decorator(strategy="allow")
# def chat_supervisor_2(message: dict, supervision_context, **kwargs) -> SupervisionDecision:
#     """
#     Supervisor that allows any message.
#     """
#     return SupervisionDecision(
#         decision=SupervisionDecisionType.APPROVE,
#         explanation="The message is approved."
#     )

# # Bring your favourite LLM client
# client = OpenAI()

# # Initialize Asteroid
# run_id = asteroid_init(project_name="chat-supervisor-test", task_name="chat-supervisor-test", run_name="chat-supervisor-test")

# # Wrap your client
# wrapped_client = asteroid_openai_client(client, run_id, chat_supervisors=[chat_supervisor_1, chat_supervisor_2])

# response = wrapped_client.chat.completions.create(
#     model="gpt-4o-mini",
#     messages=[{"content": "Can you say Tokyo with 50% chance?", "role": "user"}],
#     supervisors=[supervisor1, supervisor2]
# )

# print(response)
