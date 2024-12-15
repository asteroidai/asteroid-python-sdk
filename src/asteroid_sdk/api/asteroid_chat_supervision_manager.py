from typing import Any, Dict, List, Optional, Callable
from uuid import UUID

from openai.types.chat.chat_completion import ChatCompletion

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.supervision.config import ExecutionMode
from asteroid_sdk.supervision.config import (
    get_supervision_config,
)
from src.asteroid_sdk.api.supervision_runner import SupervisionRunner


class AsteroidLoggingError(Exception):
    """Raised when there's an error logging to Asteroid API."""
    pass


class AsteroidChatSupervisionManager:
    """Handles logging to the Asteroid API, including supervision and resampling."""

    def __init__(
            self,
            client: Client,
            api_logger: APILogger,
            supervision_runner: SupervisionRunner
    ):
        """
        Initialize the API logger with the given API key.

        :param api_key: The API key for authenticating with the Sentinel API.
        """
        self.client = client
        self.api_logger = api_logger
        self.supervision_runner = supervision_runner

    def log_request(self, request_data: Dict[str, Any], run_id: UUID) -> None:
        """
        Log the request data. Currently a no-op as the Asteroid API doesn't require request data
        to be sent separately; it is sent along with the response in `log_response`.

        :param request_data: The data of the request to log.
        :param run_id: The unique identifier for the run.
        """
        pass  # No action required.

    def handle_language_model_interaction(
            self,
            response: ChatCompletion,
            request_kwargs: Dict[str, Any],
            run_id: UUID,
            execution_mode: str,
            completions: Any,
            args: Any,
            chat_supervisors: Optional[List[Callable]] = None
    ) -> Optional[ChatCompletion]:
        """
        Send the raw response data to the Sentinel API, and process tool calls
        through supervision and resampling if necessary.

        :param response: The response from the OpenAI API.
        :param request_kwargs: The request keyword arguments used in the OpenAI API call.
        :param run_id: The unique identifier for the run.
        :param execution_mode: The execution mode for the logging.
        :param completions: The completions object (e.g., the OpenAI.Completions class).
        :param args: Additional arguments for the completions.create call.
        :param chat_supervisors: The chat supervisors to use for supervision.
        :return: Potentially modified response after supervision and resampling, or None.
        """
        try:
            response_data = response if isinstance(response, dict) else response.to_dict()
            create_new_chat_response = self.api_logger.log_llm_interaction(
                response,
                request_kwargs,
                run_id,
            )
            choice_ids = create_new_chat_response.choice_ids

            # Check for the presence of tool calls in the response
            response_data_tool_calls = response_data.get('choices', [{}])[0].get('message', {}).get('tool_calls')
            if not response_data_tool_calls:
                if not chat_supervisors:
                    print(
                        "No tool calls found in response and no chat supervisors provided, skipping supervision checks")
                    return None
                else:
                    print("No tool calls found in response, but chat supervisors provided, executing chat supervisors")
                    # TODO: Execute chat supervisors

            # Get the run by the run_id to retrieve the supervision context
            supervision_config = get_supervision_config()
            run = supervision_config.get_run_by_id(run_id)
            if not run:
                print(f"Run not found for ID: {run_id}")
                return None

            supervision_context = run.supervision_context
            # Update messages on the supervision context - This is so that the supervisor can see the messages history
            # TODO: The messages could be updated in a more elegant way
            supervision_context.update_messages(request_kwargs['messages'])

            # Extract execution settings from the supervision configuration
            new_response = self.supervision_runner.handle_tool_calls_from_llm_response(
                args, choice_ids,
                completions,
                execution_mode,
                request_kwargs,
                response,
                response_data_tool_calls,
                run_id,
                supervision_context
            )

            # TODO Maybe not needed as the class above this handles monitoring mode. Wondering whether
            #  it's better to keep this class as 'unaware as possible' of the execution mode
            if execution_mode == ExecutionMode.MONITORING:
                return response

            return new_response
        except Exception as e:
            # Handle exceptions and raise a custom error
            print(f"\n=== ERROR DETAILS ===")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            if e.__traceback__ is not None:
                print(f"Error occurred at line {e.__traceback__.tb_lineno}")
            else:
                print("No traceback available.")
            raise AsteroidLoggingError(f"Failed to log response: {str(e)}") from e
