from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.message_type import MessageType
from ..models.sentinel_message_role import SentinelMessageRole
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.sentinel_tool_call import SentinelToolCall


T = TypeVar("T", bound="SentinelMessage")


@_attrs_define
class SentinelMessage:
    """
    Attributes:
        role (SentinelMessageRole):
        content (str):
        sentinel_id (Union[Unset, str]):
        tool_calls (Union[Unset, List['SentinelToolCall']]):
        type (Union[Unset, MessageType]):
    """

    role: SentinelMessageRole
    content: str
    sentinel_id: Union[Unset, str] = UNSET
    tool_calls: Union[Unset, List["SentinelToolCall"]] = UNSET
    type: Union[Unset, MessageType] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        role = self.role.value

        content = self.content

        sentinel_id = self.sentinel_id

        tool_calls: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.tool_calls, Unset):
            tool_calls = []
            for tool_calls_item_data in self.tool_calls:
                tool_calls_item = tool_calls_item_data.to_dict()
                tool_calls.append(tool_calls_item)

        type: Union[Unset, str] = UNSET
        if not isinstance(self.type, Unset):
            type = self.type.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "role": role,
                "content": content,
            }
        )
        if sentinel_id is not UNSET:
            field_dict["sentinel_id"] = sentinel_id
        if tool_calls is not UNSET:
            field_dict["tool_calls"] = tool_calls
        if type is not UNSET:
            field_dict["type"] = type

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.sentinel_tool_call import SentinelToolCall

        d = src_dict.copy()
        role = SentinelMessageRole(d.pop("role"))

        content = d.pop("content")

        sentinel_id = d.pop("sentinel_id", UNSET)

        tool_calls = []
        _tool_calls = d.pop("tool_calls", UNSET)
        for tool_calls_item_data in _tool_calls or []:
            tool_calls_item = SentinelToolCall.from_dict(tool_calls_item_data)

            tool_calls.append(tool_calls_item)

        _type = d.pop("type", UNSET)
        type: Union[Unset, MessageType]
        if isinstance(_type, Unset):
            type = UNSET
        else:
            type = MessageType(_type)

        sentinel_message = cls(
            role=role,
            content=content,
            sentinel_id=sentinel_id,
            tool_calls=tool_calls,
            type=type,
        )

        sentinel_message.additional_properties = d
        return sentinel_message

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
