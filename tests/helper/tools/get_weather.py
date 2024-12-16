import uuid

from asteroid_sdk.api.generated.asteroid_api_client.models import Tool, ToolAttributes
from asteroid_sdk.supervision import supervise
from tests.helper.supervisors.allow_all_supervisor import allow_all_supervisor


@supervise(supervision_functions=[[allow_all_supervisor]])
def get_weather(location: str, unit: str):
    """Get the weather in a city."""
    return f"The weather in {location} is {unit}."

def get_weather_tool_object_dict(run_id: uuid.UUID, tool_id: uuid.UUID) -> Tool:
    return Tool(
        run_id=run_id,
        name="get_weather",
        description="Get the weather in a city",
        code="def get_weather(location: str, unit: str): return f'The weather in {location} is {unit}.'",
        id=tool_id,
        ignored_attributes=[],
        attributes=ToolAttributes().from_dict({'location': "<class 'str'>",'unit': "<class 'str'>"})
    )
