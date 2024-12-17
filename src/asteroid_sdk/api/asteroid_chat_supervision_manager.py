from typing import Any, Dict, List, Optional, Callable
from uuid import UUID

from openai.types.chat.chat_completion import ChatCompletion
from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.supervision.config import get_supervision_config
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.registration.helper import generate_fake_chat_tool_call


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
            chat_supervisors: Optional[List[List[Callable]]] = None
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

        # Get the run by the run_id to retrieve the supervision context
        supervision_config = get_supervision_config()
        run = supervision_config.get_run_by_id(run_id)
        if not run:
            print(f"Run not found for ID: {run_id}")
            return None

        supervision_context = run.supervision_context
        # Update messages on the supervision context
        supervision_context.update_messages(request_kwargs['messages'])

        response_data = response if isinstance(response, dict) else response.to_dict()

        # Process tool calls
        processed = self.process_tool_calls(
            response=response,
            response_data=response_data,
            supervision_context=supervision_context,
            chat_supervisors=chat_supervisors
        )

        if not processed:
            return None

        response, response_data_tool_calls = processed

        # Log the interaction
        # It needs to be after the tool calls are processed in case we switch a chat message to tool call
        create_new_chat_response = self.api_logger.log_llm_interaction(
            response,
            request_kwargs,
            run_id,
        )
        choice_ids = create_new_chat_response.choice_ids

        # Extract execution settings from the supervision configuration
        new_response = self.supervision_runner.handle_tool_calls_from_llm_response(
            args=args,
            choice_ids=choice_ids,
            completions=completions,
            execution_mode=execution_mode,
            request_kwargs=request_kwargs,
            response=response,
            response_data_tool_calls=response_data_tool_calls,
            run_id=run_id,
            supervision_context=supervision_context,
            chat_supervisors=chat_supervisors  
        )

        return new_response

    def process_tool_calls(
            self,
            response: ChatCompletion,
            response_data: Dict[str, Any],
            supervision_context: Any,
            chat_supervisors: Optional[List[List[Callable]]] = None
    ) -> Optional[tuple]:
        """
        Process the tool calls from the response data. If no tool calls are found,
        handle accordingly based on the presence of chat supervisors.

        :param response: The original ChatCompletion response from the OpenAI API.
        :param response_data: The response data as a dictionary.
        :param supervision_context: The supervision context associated with the run.
        :param chat_supervisors: A list of chat supervisor callables.
        :return: A tuple of (modified_response, response_data_tool_calls) or None.
        """
        response_data_tool_calls = response_data.get('choices', [{}])[0].get('message', {}).get('tool_calls')

        if response_data_tool_calls:
            return None  # No processing needed

        if not chat_supervisors:
            print(
                "No tool calls found in response and no chat supervisors provided, only logging the messages to Asteroid")
            self.api_logger.log_llm_interaction(
                response,
                request_kwargs={},  # Pass actual request_kwargs if needed
                run_id=UUID(int=0)  # Pass actual run_id if needed
            )
            return None

        # Use the extracted function to generate fake tool calls
        modified_response, response_data_tool_calls = generate_fake_chat_tool_call(
            client=self.client,
            response=response,
            supervision_context=supervision_context,
            chat_supervisors=chat_supervisors
        )
        print("No tool calls found in response, but chat supervisors provided, executing chat supervisors")

        return modified_response, response_data_tool_calls
