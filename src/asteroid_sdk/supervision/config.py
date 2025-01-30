import copy
import json
import random
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID
from inspect_ai.tool import ToolCall
from openai.types.chat.chat_completion_message import ChatCompletionMessageToolCall
from anthropic.types import Message, TextBlock, ToolUseBlock
from pydantic import BaseModel, Field
import logging

from asteroid_sdk.supervision.helpers.model_provider_helper import Provider

DEFAULT_RUN_NAME = "default"

class SupervisionDecisionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    TERMINATE = "terminate"
    MODIFY = "modify"

class ExecutionMode(str, Enum):
    MONITORING = "monitoring"
    SUPERVISION = "supervision"

class RejectionPolicy(str, Enum):
    RESAMPLE_WITH_FEEDBACK = "resample_with_feedback"
    NO_RESAMPLE = "no_resample"

class MultiSupervisorResolution(str, Enum):
    ALL_MUST_APPROVE = "all_must_approve"
    #TODO: We will support more complex resolution strategies in the future



class ModifiedData(BaseModel):
    tool_name: Optional[str] = None
    """Name of the tool/function."""

    tool_args: Optional[List[Any]] = None
    """Modified positional arguments for the tool/function."""

    tool_kwargs: Optional[Dict[str, Any]] = None
    """Modified keyword arguments for the tool/function."""

    original_inspect_ai_call: Optional[ToolCall] = None
    """Original InspectAI call that was modified."""

    openai_tool_call: Optional[ChatCompletionMessageToolCall] = None
    """New OpenAI tool call that was createdcreated."""
    
    

class SupervisionDecision(BaseModel):
    decision: SupervisionDecisionType
    """Supervision decision."""

    modified: Optional[ModifiedData] = Field(default=None)
    """Modified data for decision 'modify'."""

    explanation: Optional[str] = Field(default=None)
    """Explanation for decision."""

class SupervisionContext:
    """
    Context for supervision decisions. This is used to store the context of the currently active project including all tasks/runs.
    """
    def __init__(self, pending_functions: Optional[Dict[str, Dict[str, Any]]] = None):
        self.lock = Lock()  # Ensure thread safety
        self.metadata: Dict[str, Any] = {}
        self.openai_messages: List[Dict[str, Any]] = []
        self.anthropic_messages: List[Dict[str, Any]] = []
        self.gemini_messages: List[Dict[str, Any]] = []
        self.supervised_functions_registry: Dict[str, Dict[str, Any]] = pending_functions or {}
        self.registered_supervisors: Dict[str, UUID] = {}
        self.local_supervisors_by_id: Dict[UUID, Callable] = {}

    def add_metadata(self, key: str, value: Any):
        self.metadata[key] = value

    def messages_to_text(self) -> str:
        """Converts the supervision context into a textual description."""

        with self.lock:
            # Process OpenAI messages if any
            if self.openai_messages:
                return self._describe_openai_messages()
            elif self.anthropic_messages:
                return self._describe_anthropic_messages()
            elif self.gemini_messages:
                return self._describe_gemini_messages()

        logging.warning("No messages to convert to text")
        return ""

    def _describe_openai_messages(self) -> str:
        """Converts the openai_messages into a textual description."""
        messages_text = []
        for message in self.openai_messages:
            role = message.get('role', 'Unknown').capitalize()
            content = message.get('content', '')
            if type(content) == str:
                content = content.strip()
            elif type(content) == list:
                # TODO: Solve this - it happens when there is an image
                content = ''
                for m in content:
                    if m.type == 'text':
                        content += m.text
                    elif m.type == 'image_url':
                        content += f'Image' #{m.image_url}' #TODO: Add the image somehow
                
            message_str = f"**{role}:**\n{content}" if content else f"**{role}:**"

            # Handle tool calls if present
            tool_calls = message.get('tool_calls', [])
            if tool_calls:
                for tool_call in tool_calls:
                    function = tool_call.get('function', {})
                    function_name = function.get('name', 'Unknown Function')
                    arguments = function.get('arguments', '{}').strip()
                    message_str += f"\n\n**Function Call:** `{function_name}`\n**Arguments:** {arguments}"

            messages_text.append(message_str)
        return "\n\n".join(messages_text)


    def _describe_anthropic_messages(self) -> str:
        """Converts the anthropic_messages into a textual description, including tool calls."""
        messages_text = []
        for message in self.anthropic_messages:
            role = message.get('role', 'Unknown').capitalize()
            contents = message.get('content', [])

            message_str = f"**{role}:**"

            if isinstance(contents, str):
                message_str += f"\n{contents}"
            else:
                for content_block in contents:
                    if isinstance(content_block, str):
                        message_str += f"\n{content_block}"
                    elif isinstance(content_block, TextBlock):
                        text = content_block.text.strip()
                        if text:
                            message_str += f"\n{text}"
                    elif isinstance(content_block, ToolUseBlock):
                        tool_name = content_block.name
                        tool_args = content_block.input
                        message_str += f"\n\n**Tool Use:** `{tool_name}`\n**Arguments:** {json.dumps(tool_args, indent=2)}"
                    else:
                        message_str += f"\n\n**Unknown Content Block Type:** {type(content_block)}"

            messages_text.append(message_str)

        return "\n\n".join(messages_text)


    def _describe_gemini_messages(self) -> str:
        """Converts the gemini_messages into a textual description."""
        messages_text = []
        for message in self.gemini_messages:
            for part in message.parts:
                messages_text.append(f"**{message.role}:**\n{part.text}")
                if part.function_call:
                    params = {arg: value for arg, value in part.function_call.args.items()}
                    messages_text.append(f"**Tool Use:**\n{part.function_call.name}\n**Arguments:** {json.dumps(params, indent=2)}")
        return "\n\n".join(messages_text)

    # Methods to manage the supervised functions registry
    def add_supervised_function(
        self,
        function_name: str,
        supervision_functions: Optional[List[List[Callable]]] = None,
        ignored_attributes: Optional[List[str]] = None,
        function: Optional[Callable | Dict[str, Any]] = None,
        tool_id: Optional[UUID] = None,
    ):
        """
        Registers a supervised function or tool in the context.

        Args:
            function_name (str): The name of the function/tool.
            supervision_functions (Optional[List[List[Callable]]]): The supervision functions.
            ignored_attributes (Optional[List[str]]): Attributes to ignore.
            function (Optional[Callable]): The function object, if available.
            tool_id (Optional[UUID]): The ID of the tool, if available.
        """
        with self.lock:
            if function_name in self.supervised_functions_registry:
                logging.info(f"Function '{function_name}' is already registered in context. Skipping.")
                return  # Skip adding the duplicate

            self.supervised_functions_registry[function_name] = {
                'supervision_functions': supervision_functions or [],
                'ignored_attributes': ignored_attributes or [],
                'function': function,  # This will be None if function is not provided
                'tool_id': tool_id,
            }
            logging.info(f"Registered function '{function_name}' in supervision context")

    def update_tool_id(self, function_name: str, tool_id: UUID):
        with self.lock:
            if function_name in self.supervised_functions_registry:
                self.supervised_functions_registry[function_name]['tool_id'] = tool_id
                logging.info(f"Updated tool ID for '{function_name}' to {tool_id}")
            else:
                logging.error(f"Function '{function_name}' not found in supervision context.")

    def add_run_id_to_supervised_function(self, function_name: str, run_id: UUID):
        with self.lock:
            if function_name in self.supervised_functions_registry:
                self.supervised_functions_registry[function_name]['run_id'] = run_id
                logging.info(f"Updated run ID for '{function_name}' to {run_id}")
            else:
                logging.error(f"Function '{function_name}' not found in supervision context.")

    def get_supervised_function_entry(self, function_name: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.supervised_functions_registry.get(function_name)

    def get_supervised_functions(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.supervised_functions_registry.values())

    def add_supervisor_id(self, supervisor_name: str, supervisor_id: UUID):
        with self.lock:
            self.registered_supervisors[supervisor_name] = supervisor_id
            logging.info(f"Locally registered supervisor '{supervisor_name}' with ID: {supervisor_id}")

    def get_supervisor_id(self, supervisor_name: str) -> Optional[UUID]:
        with self.lock:
            return self.registered_supervisors.get(supervisor_name)

    def update_messages(self, messages: List[Dict[str, Any]], provider: Provider, system_message: Optional[str] = None):
        """Updates the context with a list of OpenAI messages."""
        if system_message:
            # Anthropic stores the system message outside of the messages list
            final_messages = [{"role": "system", "content": system_message}] + messages['messages'].copy()
        else:
            final_messages = messages['messages'].copy()

        with self.lock:
            if provider == Provider.ANTHROPIC:
                self.anthropic_messages = final_messages
            elif provider == Provider.OPENAI:
                self.openai_messages = final_messages
            elif provider == Provider.GEMINI:
                self.gemini_messages = final_messages

    def add_local_supervisor(self, supervisor_id: UUID, supervisor_func: Callable):
        """Add a supervisor function to the config."""
        self.local_supervisors_by_id[supervisor_id] = supervisor_func

    def get_supervisor_func_by_id(self, supervisor_id: UUID) -> Optional[Callable]:
        """Retrieve a supervisor function by its ID."""
        return self.local_supervisors_by_id.get(supervisor_id)

    def get_supervisor_id_by_name(self, supervisor_name: str) -> Optional[UUID]:
        """Retrieve a supervisor function by its function."""
        for supervisor_id, func in self.local_supervisors_by_id.items():
            if func.__name__ == supervisor_name:
                return supervisor_id
        return None

class Run(BaseModel):
    run_id: UUID
    run_name: str
    supervision_context: SupervisionContext = Field(default_factory=SupervisionContext)

    class Config:
        arbitrary_types_allowed = True

class Task(BaseModel):
    task_id: UUID
    task_name: str
    runs: Dict[str, Run] = Field(default_factory=dict)

class Project(BaseModel):
    project_id: UUID
    project_name: str
    tasks: Dict[str, Task] = Field(default_factory=dict)


class SupervisionConfig:
    def __init__(self):
        self.global_supervision_functions: List[Callable] = []
        self.override_local_policy = False
        self.llm = None
        self.client = None  # Sentinel API client
        self.execution_settings: Dict[str, Any] = {}

        # Hierarchical projects structure
        self.projects: Dict[str, Project] = {}  # Mapping from project_name to Project
        self.projects_by_id: Dict[UUID, Project] = {}
        self.tasks_by_id: Dict[UUID, Task] = {}
        self.runs_by_id: Dict[UUID, Run] = {}
        self.runs_by_name: Dict[str, List[Run]] = {}  # New mapping for runs by name
        self.lock = Lock()  # For thread safety
        self.pending_supervised_functions: Dict[str, Dict[str, Any]] = {}

    def set_global_supervision_functions(self, functions: List[Callable]):
        self.global_supervision_functions = functions

    def set_llm(self, llm):
        self.llm = llm

    def set_execution_settings(self, execution_settings: Dict[str, Any]):
        self.execution_settings = execution_settings

    # Project methods
    def add_project(self, project_name: str, project_id: UUID):
        """Add a new project."""
        project = Project(project_id=project_id, project_name=project_name)
        self.projects[project_name] = project
        self.projects_by_id[project_id] = project  # Add to ID-based dict

    def get_project(self, project_name: str) -> Optional[Project]:
        """Retrieve a project by its name."""
        return self.projects.get(project_name)

    def get_project_by_id(self, project_id: UUID) -> Optional[Project]:
        """Retrieve a project by its ID."""
        return self.projects_by_id.get(project_id)

    # Task methods
    def add_task(self, project_name: str, task_name: str, task_id: UUID):
        """Add a new task to a project."""
        project = self.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' does not exist.")
        task = Task(task_id=task_id, task_name=task_name)
        project.tasks[task_name] = task
        self.tasks_by_id[task_id] = task  # Add to ID-based dict

    def get_task(self, project_name: str, task_name: str) -> Optional[Task]:
        """Retrieve a task by its name under a project."""
        project = self.get_project(project_name)
        if project:
            return project.tasks.get(task_name)
        return None

    def get_task_by_id(self, task_id: UUID) -> Optional[Task]:
        """Retrieve a task by its ID."""
        return self.tasks_by_id.get(task_id)

    # Run methods
    # TODO: why so object lookup by string name kekpog
    def add_run(self, project_name: str, task_name: str, run_name: str, run_id: UUID):
        """Add a new run to a task under a project."""
        with self.lock:
            task = self.get_task(project_name, task_name)
            if not task:
                raise ValueError(f"Task '{task_name}' does not exist under project '{project_name}'.")

            # Obtain a copy of the pending functions
            supervision_context = SupervisionContext(
                pending_functions=self.pending_supervised_functions
            )
            logging.info("Initialized supervised functions registry with pending functions.")

            # Optionally, clear the pending supervised functions
            # self.clear_pending_supervised_functions()

            run = Run(
                run_id=run_id,
                run_name=run_name,
                supervision_context=supervision_context
            )
            task.runs[run_name] = run
            self.runs_by_id[run_id] = run

            # Add to name-based dict
            if run_name not in self.runs_by_name:
                self.runs_by_name[run_name] = []
            self.runs_by_name[run_name].append(run)

    def get_run(self, project_name: str, task_name: str, run_name: str) -> Optional[Run]:
        """Retrieve a run by its name under a task and project."""
        task = self.get_task(project_name, task_name)
        if task:
            return task.runs.get(run_name)
        return None

    def get_run_by_id(self, run_id: UUID) -> Optional[Run]:
        """Retrieve a run by its ID."""
        return self.runs_by_id.get(run_id)

    def get_run_by_name(self, run_name: str) -> Optional[Run]:
        """Retrieve a run by its name across all projects and tasks."""
        for run in self.runs_by_name.get(run_name, []):
            return run
        return None

    def get_all_runs(self) -> List[Run]:
        """Retrieve all runs across all projects and tasks."""
        return list(self.runs_by_id.values())

    # Optional editing methods
    def update_project_id(self, project_name: str, new_project_id: UUID):
        """Update the project ID for a given project name."""
        project = self.projects.get(project_name)
        if project:
            project.project_id = new_project_id
        else:
            raise ValueError(f"Project '{project_name}' does not exist.")

    def update_task_id(self, project_name: str, task_name: str, new_task_id: UUID):
        """Update the task ID for a given task name under a project."""
        project = self.projects.get(project_name)
        if project:
            task = project.tasks.get(task_name)
            if task:
                task.task_id = new_task_id
            else:
                raise ValueError(f"Task '{task_name}' does not exist under project '{project_name}'.")
        else:
            raise ValueError(f"Project '{project_name}' does not exist.")

    def update_run_id(self, project_name: str, task_name: str, run_name: str, new_run_id: UUID):
        """Update the run ID for a given run name under a task and project."""
        project = self.projects.get(project_name)
        if project:
            task = project.tasks.get(task_name)
            if task:
                if run_name in task.runs:
                    task.runs[run_name].run_id = new_run_id
                else:
                    raise ValueError(f"Run '{run_name}' does not exist under task '{task_name}' and project '{project_name}'.")
            else:
                raise ValueError(f"Task '{task_name}' does not exist under project '{project_name}'.")
        else:
            raise ValueError(f"Project '{project_name}' does not exist.")

    def update_supervision_context_by_run_id(self, run_id: UUID, new_supervision_context: SupervisionContext):
        """Update the supervision context for a run specified by run_id."""
        run = self.get_run_by_id(run_id)
        if run:
            run.supervision_context = new_supervision_context
            logging.info(f"Updated supervision context for run_id {run_id}")
        else:
            raise ValueError(f"No run found with run_id {run_id}")

    def update_supervision_context_by_run_name(
        self,
        run_name: str,
        new_supervision_context: SupervisionContext,
    ):
        """Update the supervision context for a run specified by run_name."""
        with self.lock:
            runs = self.runs_by_name.get(run_name)
            if runs:
                if len(runs) == 1:
                    run = runs[0]
                else:
                    raise ValueError(
                        f"Multiple runs found with run_name '{run_name}'. Please specify project and task names."
                    )
                run.supervision_context = new_supervision_context
                logging.info(f"Updated supervision context for run_name '{run_name}'")
            else:
                raise ValueError(f"No run found with run_name '{run_name}'")

    # Method to register supervised functions temporarily
    def register_pending_supervised_function(
        self,
        tool: Callable | Dict[str, Any],
        supervision_functions: Optional[List[List[Callable]]] = None,
        ignored_attributes: Optional[List[str]] = None,
    ):
        if isinstance(tool, dict):
            tool_name = tool.get('name')
        else:
            tool_name = tool.__qualname__
        if not tool_name:
            raise ValueError("Tool name not found. Please provide a tool name.")
        with self.lock:
            if tool_name in self.pending_supervised_functions:
                logging.info(f"Function '{tool_name}' is already pending registration. Skipping.")
                return  # Skip adding the duplicate

            if isinstance(tool, dict):
                tool_description = str(tool.get('description'))
                function = tool.get('function')
            else:
                tool_description = str(tool.__doc__) if tool.__doc__ else tool.__qualname__
                function = tool

            self.pending_supervised_functions[tool_name] = {
                'supervision_functions': supervision_functions or [],
                'ignored_attributes': ignored_attributes or [],
                'function': function,
                'tool_description': tool_description,
            }
            logging.info(f"Registered pending supervised function '{tool_name}'")

    def get_pending_supervised_functions(self) -> Dict[str, Dict[str, Any]]:
        """Returns a deep copy of the pending supervised functions."""
        with self.lock:
            return copy.deepcopy(self.pending_supervised_functions)


def get_supervision_context(run_id: UUID, project_name: Optional[str] = None, task_name: Optional[str] = None, run_name: Optional[str] = None) -> SupervisionContext:
    if project_name and task_name and run_name:
        run = supervision_config.get_run(project_name, task_name, run_name)
    else:
        run = supervision_config.get_run_by_id(run_id)
    if run:
        return run.supervision_context
    else:
        raise ValueError(f"No run found with run_id {run_id}")

def set_global_supervision_functions(functions: List[Callable]):
    supervision_config.set_global_supervision_functions(functions)

# Global instance of SupervisionConfig
supervision_config = SupervisionConfig()

def get_supervision_config():
    return supervision_config
