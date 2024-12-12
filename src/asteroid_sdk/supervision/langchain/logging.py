import os
import json
from datetime import datetime
from uuid import UUID
from typing import Any, Dict, Optional, List
from collections.abc import Sequence
from langchain_core.callbacks import BaseCallbackHandler
from langchain.schema import BaseMessage, LLMResult, Document
from tenacity import RetryCallState
from langchain.tools import BaseTool
from langchain_core.messages import messages_to_dict
import inspect

from entropy_labs.supervision.config import supervision_config

class EntropyLabsCallbackHandler(BaseCallbackHandler):
    def __init__(self, tools: List[BaseTool], log_directory=".logs/langchain", single_log_file=False, log_filename=None, run_id: Optional[UUID] = None) -> None:
        super().__init__()
        self.raise_error = True
        self.run_inline = True
        self.log_directory = log_directory
        self.tools = tools
        # Create log directory if it doesn't exist
        os.makedirs(self.log_directory, exist_ok=True)
        self.single_log_file = single_log_file
        self.log_filename = log_filename
        if self.single_log_file:
            # Determine the log file path
            if self.log_filename:
                self.log_filepath = os.path.join(self.log_directory, self.log_filename)
            else:
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.log_filepath = os.path.join(self.log_directory, f"single_log_{current_time}.log")
            # Open the log file in append mode
            self.log_file = open(self.log_filepath, 'a', encoding='utf-8')
        # Initialize self.trace_logs in all cases
        self.trace_logs: Dict[UUID, Any] = {}
        # Map of run_id to trace_id
        self.run_trace_ids: Dict[UUID, UUID] = {}
        self.run_id = run_id
        

    def _get_log_file(self, trace_id: UUID):
        if self.single_log_file:
            return self.log_file
        else:
            if trace_id not in self.trace_logs:
                # Get the current date and time
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Create a filename with the timestamp
                filename = os.path.join(self.log_directory, f"{trace_id}_{current_time}.log")
                # Open the file in append mode
                self.trace_logs[trace_id] = open(filename, 'a', encoding='utf-8')
            return self.trace_logs[trace_id]

    def _close_log_file(self, trace_id: UUID):
        if self.single_log_file:
            if self.log_file:
                self.log_file.close()
                self.log_file = None
        else:
            if trace_id in self.trace_logs:
                self.trace_logs[trace_id].close()
                del self.trace_logs[trace_id]

    def _serialize_data(self, data: Any) -> Any:
        if isinstance(data, UUID):
            return str(data)
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif isinstance(data, dict):
            return {self._serialize_data(k): self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_data(item) for item in data]
        elif hasattr(data, '__dict__'):
            return self._serialize_data(vars(data))
        else:
            return str(data)

    def _log_event(self, event_name: str, run_id: UUID, parent_run_id: Optional[UUID], data: Dict[str, Any], trace_id: UUID):
        log_file = self._get_log_file(trace_id)
        event_data = {
            "event": event_name,
            "time": datetime.now().isoformat(),
            "run_id": str(run_id),
            "parent_run_id": str(parent_run_id) if parent_run_id else None,
            "trace_id": str(trace_id),
            "data": self._serialize_data(data),
        }
        log_file.write(json.dumps(event_data) + '\n')
        log_file.flush()

        # Add the event data to the SupervisionContext
        supervision_config.context.add_event(event_data)

    def _get_trace_id(self, run_id: UUID, parent_run_id: Optional[UUID]) -> UUID:
        if parent_run_id is None:
            # Top-level run; use its own run_id as trace_id
            trace_id = run_id
        else:
            # Child run; inherit trace_id from parent
            trace_id = self.run_trace_ids.get(parent_run_id, parent_run_id)
        # Map current run_id to trace_id
        self.run_trace_ids[run_id] = trace_id
        return trace_id

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID]=None,
        **kwargs: Any
    ) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        
        # Extract functions from invocation_params
        invocation_params = kwargs.get('invocation_params', {})
        functions = invocation_params.get('functions', [])
        
        # Retrieve function code
        function_code_dict = {}
        for func_spec in functions:
            func_name = func_spec.get('name')
            if func_name:
                try:
                    tool = next((t for t in self.tools if t.name == func_name), None)
                    if tool:
                        function_code_dict[func_name] = get_tool_code(tool)
                    else:
                        function_code_dict[func_name] = "Tool implementation not found."
                except Exception as e:
                    function_code_dict[func_name] = f"Error retrieving source code: {str(e)}"
                    
        data = {
            "serialized": serialized,
            "messages": [messages_to_dict(conversation) for conversation in messages], 
            "kwargs": kwargs,
            "function_implementations": function_code_dict  # Include function code
        }
        self._log_event("on_chat_model_start", run_id, parent_run_id, data, trace_id)

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any
    ) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {
            "serialized": serialized,
            "prompts": prompts,
            "kwargs": kwargs,
        }
        self._log_event("on_llm_start", run_id, parent_run_id, data, trace_id)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {
            "response": self._serialize_data(response),
            "kwargs": kwargs,
        }
        self._log_event("on_llm_end", run_id, parent_run_id, data, trace_id)
        # Close the log file upon top-level LLM end if not using single log file
        if parent_run_id is None and not self.single_log_file:
            self._close_log_file(trace_id)

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any
    ) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"serialized": serialized, "inputs": inputs, "kwargs": kwargs}
        self._log_event("on_chain_start", run_id, parent_run_id, data, trace_id)

    def on_chain_end(self, outputs: Dict[str, Any], *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"outputs": outputs, "kwargs": kwargs}
        self._log_event("on_chain_end", run_id, parent_run_id, data, trace_id)
        # Close the log file upon top-level chain end
        if parent_run_id is None:
            self._close_log_file(trace_id)

    def on_chain_error(self, error: BaseException, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"error": str(error)}
        self._log_event("on_chain_error", run_id, parent_run_id, data, trace_id)
        # Close the log file upon top-level chain error
        if parent_run_id is None:
            self._close_log_file(trace_id)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID]=None,
        **kwargs: Any
    ) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        tool_name = serialized.get('name')

        # Retrieve tool implementation using the reusable function
        tool_code = "Tool implementation not found."
        if tool_name:
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if tool:
                tool_code = get_tool_code(tool)

        data = {
            "serialized": serialized,
            "input_str": input_str,
            "kwargs": kwargs,
            "tool_code": tool_code  # Include tool implementation
        }
        self._log_event("on_tool_start", run_id, parent_run_id, data, trace_id)

    def on_tool_end(self, output: Any, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"output": self._serialize_data(output), "kwargs": kwargs}
        self._log_event("on_tool_end", run_id, parent_run_id, data, trace_id)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"error": str(error)}
        self._log_event("on_tool_error", run_id, parent_run_id, data, trace_id)

    def on_text(self, text: str, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"text": text, "kwargs": kwargs}
        self._log_event("on_text", run_id, parent_run_id, data, trace_id)

    def on_retry(self, retry_state: RetryCallState, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"retry_state": self._serialize_data(retry_state)}
        self._log_event("on_retry", run_id, parent_run_id, data, trace_id)

    def on_llm_new_token(self, token: str, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"token": token, "kwargs": kwargs}
        self._log_event("on_llm_new_token", run_id, parent_run_id, data, trace_id)

    def on_llm_error(self, error: BaseException, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"error": str(error)}
        self._log_event("on_llm_error", run_id, parent_run_id, data, trace_id)

    def on_retriever_start(self, serialized: Dict[str, Any], query: str, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"serialized": serialized, "query": query, "kwargs": kwargs}
        self._log_event("on_retriever_start", run_id, parent_run_id, data, trace_id)

    def on_retriever_end(self, documents: Sequence[Document], *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"documents": self._serialize_data(documents), "kwargs": kwargs}
        self._log_event("on_retriever_end", run_id, parent_run_id, data, trace_id)

    def on_retriever_error(self, error: BaseException, *, run_id: UUID, parent_run_id: Optional[UUID]=None, **kwargs: Any) -> None:
        trace_id = self._get_trace_id(run_id, parent_run_id)
        data = {"error": str(error)}
        self._log_event("on_retriever_error", run_id, parent_run_id, data, trace_id)

    def __del__(self):
        # Close any open log files
        if self.single_log_file and getattr(self, 'log_file', None):
            self.log_file.close()
            self.log_file = None
        else:
            for log_file in self.trace_logs.values():
                log_file.close()
            self.trace_logs.clear()

def get_tool_code(tool: BaseTool) -> str:
    """Retrieve the source code of a tool's function."""
    try:
        # Access the 'func' attribute of the tool
        func = getattr(tool, 'func', None)
        if callable(func):
            return inspect.getsource(func)
        else:
            return "Function implementation not found."
    except Exception as e:
        return f"Error retrieving source code: {str(e)}"

