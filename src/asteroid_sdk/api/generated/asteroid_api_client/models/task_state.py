from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.message import Message
    from ..models.output import Output
    from ..models.task_state_metadata import TaskStateMetadata
    from ..models.task_state_store import TaskStateStore
    from ..models.tool import Tool
    from ..models.tool_choice import ToolChoice


T = TypeVar("T", bound="TaskState")


@_attrs_define
class TaskState:
    """
    Attributes:
        messages (List['Message']):
        tools (List['Tool']):
        output (Output):
        completed (bool):
        tool_choice (Union[Unset, ToolChoice]):
        store (Union[Unset, TaskStateStore]):
        metadata (Union[Unset, TaskStateMetadata]):
    """

    messages: List["Message"]
    tools: List["Tool"]
    output: "Output"
    completed: bool
    tool_choice: Union[Unset, "ToolChoice"] = UNSET
    store: Union[Unset, "TaskStateStore"] = UNSET
    metadata: Union[Unset, "TaskStateMetadata"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        messages = []
        for messages_item_data in self.messages:
            messages_item = messages_item_data.to_dict()
            messages.append(messages_item)

        tools = []
        for tools_item_data in self.tools:
            tools_item = tools_item_data.to_dict()
            tools.append(tools_item)

        output = self.output.to_dict()

        completed = self.completed

        tool_choice: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.tool_choice, Unset):
            tool_choice = self.tool_choice.to_dict()

        store: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.store, Unset):
            store = self.store.to_dict()

        metadata: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.metadata, Unset):
            metadata = self.metadata.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "messages": messages,
                "tools": tools,
                "output": output,
                "completed": completed,
            }
        )
        if tool_choice is not UNSET:
            field_dict["tool_choice"] = tool_choice
        if store is not UNSET:
            field_dict["store"] = store
        if metadata is not UNSET:
            field_dict["metadata"] = metadata

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.message import Message
        from ..models.output import Output
        from ..models.task_state_metadata import TaskStateMetadata
        from ..models.task_state_store import TaskStateStore
        from ..models.tool import Tool
        from ..models.tool_choice import ToolChoice

        d = src_dict.copy()
        messages = []
        _messages = d.pop("messages")
        for messages_item_data in _messages:
            messages_item = Message.from_dict(messages_item_data)

            messages.append(messages_item)

        tools = []
        _tools = d.pop("tools")
        for tools_item_data in _tools:
            tools_item = Tool.from_dict(tools_item_data)

            tools.append(tools_item)

        output = Output.from_dict(d.pop("output"))

        completed = d.pop("completed")

        _tool_choice = d.pop("tool_choice", UNSET)
        tool_choice: Union[Unset, ToolChoice]
        if isinstance(_tool_choice, Unset):
            tool_choice = UNSET
        else:
            tool_choice = ToolChoice.from_dict(_tool_choice)

        _store = d.pop("store", UNSET)
        store: Union[Unset, TaskStateStore]
        if isinstance(_store, Unset):
            store = UNSET
        else:
            store = TaskStateStore.from_dict(_store)

        _metadata = d.pop("metadata", UNSET)
        metadata: Union[Unset, TaskStateMetadata]
        if isinstance(_metadata, Unset):
            metadata = UNSET
        else:
            metadata = TaskStateMetadata.from_dict(_metadata)

        task_state = cls(
            messages=messages,
            tools=tools,
            output=output,
            completed=completed,
            tool_choice=tool_choice,
            store=store,
            metadata=metadata,
        )

        task_state.additional_properties = d
        return task_state

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
