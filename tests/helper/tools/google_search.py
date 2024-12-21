import uuid

from asteroid_sdk.api.generated.asteroid_api_client.models import Tool, ToolAttributes
from asteroid_sdk.supervision import supervise
from tests.helper.supervisors.depends_on_tool_call_supervisor import depends_on_tool_call_supervisor


@supervise(supervision_functions=[[depends_on_tool_call_supervisor]])
def google_search(query_string: str):
    """Get the weather in a city."""
    return f"Searched {query_string}."

def get_google_search_tool_object_dict(run_id: uuid.UUID, tool_id: uuid.UUID) -> Tool:
    return Tool(
        run_id=run_id,
        name="google_search",
        description="Search for a query string",
        code="def google_search(query_string: str): return f'Searched {query_string}.'",
        id=tool_id,
        ignored_attributes=[],
        attributes=ToolAttributes().from_dict({'query_string': "<class 'str'>"})
    )
