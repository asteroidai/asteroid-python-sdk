import uuid
from http import HTTPStatus
from typing import Any, List
from typing import Dict
from unittest.mock import MagicMock

from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.generated.asteroid_api_client.models import Tool
from asteroid_sdk.registration.initialise_project import asteroid_init
from asteroid_sdk.supervision.config import ExecutionMode, RejectionPolicy, MultiSupervisorResolution
from tests.helper.api.mock_api import make_created_response, make_created_response_with_id, make_response


class InitAsteroidForTestsConfig:
    def __init__(
            self,
            project_id: uuid.UUID,
            task_id: uuid.UUID,
            run_id: uuid.UUID,
            execution_settings: Dict[str, Any],
            tool_list: List[Tool]
    ):
        self.project_id = project_id
        self.task_id = task_id
        self.run_id = run_id
        self.execution_settings = execution_settings
        self.tool_list = tool_list


def init_asteroid_for_tests(client: MagicMock(Client), config_for_tests: InitAsteroidForTestsConfig) -> None:
    """
    This method is used to initialise Asteroid for some tests. It mocks out the API calls that are made when
    initialising the package. We have to initialise to be able to get all data in the context.

    Args:
        client: MagicMock(Client)
        config_for_tests: InitAsteroidForTestsConfig

    Returns:
        None

    """

    # Init functions need these
    project_created_response = make_created_response_with_id(config_for_tests.project_id)
    task_created_response = make_created_response_with_id(config_for_tests.task_id)
    run_created_response = make_created_response_with_id(config_for_tests.run_id)
    # src/asteroid_sdk/registration/helper.py:319
    # create_run_tool_sync_detailed in helper
    responses_that_need_to_happen_per_tool = []
    for tool in config_for_tests.tool_list:
        responses_that_need_to_happen_per_tool.append(make_response(tool.to_dict(), HTTPStatus.CREATED))
        # This is a hack to use same ID for both tool and supervisor. Makes test easier. Not long term solution
        responses_that_need_to_happen_per_tool.append(make_created_response_with_id(tool.id))
        # This is a hack to use same ID for both tool and supervisor and chain. Makes test easier. Not long term solution
        responses_that_need_to_happen_per_tool.append(make_created_response([str(tool.id)]))

    # src/asteroid_sdk/registration/helper.py:318

    # Mocked out the API calls. This is going to be difficult to fix if not using a debugger, if we ever change
    #  how we do init
    client.get_httpx_client.return_value.request.side_effect = [
        project_created_response,
        task_created_response,
        run_created_response,
        *responses_that_need_to_happen_per_tool,
    ]

    EXECUTION_SETTINGS = {
        "execution_mode": ExecutionMode.SUPERVISION,
        # can be "monitoring" or "supervision", monitoring is async and supervision is sync by default
        "allow_tool_modifications": True,  # allow the tool to be modified by the supervisor
        "rejection_policy": RejectionPolicy.RESAMPLE_WITH_FEEDBACK,
        # policy to use when the supervisor rejects the tool call
        "n_resamples": 3,  # number of resamples to use when the supervisor rejects the tool call
        "multi_supervisor_resolution": MultiSupervisorResolution.ALL_MUST_APPROVE,
        # resolution strategy when multiple supervisors are running in parallel
        "remove_feedback_from_context": True,  # remove the feedback from the context
    }
    # BOOTSTRAP
    asteroid_init(execution_settings=EXECUTION_SETTINGS)
