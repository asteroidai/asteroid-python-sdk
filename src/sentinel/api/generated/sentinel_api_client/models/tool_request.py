from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.arguments import Arguments
    from ..models.message import Message
    from ..models.task_state import TaskState


T = TypeVar("T", bound="ToolRequest")


@_attrs_define
class ToolRequest:
    """
    Attributes:
        tool_id (UUID):
        message (Message):
        arguments (Arguments):
        task_state (TaskState):
        id (Union[Unset, UUID]):
        requestgroup_id (Union[Unset, UUID]):
    """

    tool_id: UUID
    message: "Message"
    arguments: "Arguments"
    task_state: "TaskState"
    id: Union[Unset, UUID] = UNSET
    requestgroup_id: Union[Unset, UUID] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        tool_id = str(self.tool_id)

        message = self.message.to_dict()

        arguments = self.arguments.to_dict()

        task_state = self.task_state.to_dict()

        id: Union[Unset, str] = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        requestgroup_id: Union[Unset, str] = UNSET
        if not isinstance(self.requestgroup_id, Unset):
            requestgroup_id = str(self.requestgroup_id)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "tool_id": tool_id,
                "message": message,
                "arguments": arguments,
                "task_state": task_state,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if requestgroup_id is not UNSET:
            field_dict["requestgroup_id"] = requestgroup_id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.arguments import Arguments
        from ..models.message import Message
        from ..models.task_state import TaskState

        d = src_dict.copy()
        tool_id = UUID(d.pop("tool_id"))

        message = Message.from_dict(d.pop("message"))

        arguments = Arguments.from_dict(d.pop("arguments"))

        task_state = TaskState.from_dict(d.pop("task_state"))

        _id = d.pop("id", UNSET)
        id: Union[Unset, UUID]
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        _requestgroup_id = d.pop("requestgroup_id", UNSET)
        requestgroup_id: Union[Unset, UUID]
        if isinstance(_requestgroup_id, Unset):
            requestgroup_id = UNSET
        else:
            requestgroup_id = UUID(_requestgroup_id)

        tool_request = cls(
            tool_id=tool_id,
            message=message,
            arguments=arguments,
            task_state=task_state,
            id=id,
            requestgroup_id=requestgroup_id,
        )

        tool_request.additional_properties = d
        return tool_request

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
