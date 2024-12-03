from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.sentinel_tool_call_type import SentinelToolCallType
from ..types import UNSET, Unset

T = TypeVar("T", bound="SentinelToolCall")


@_attrs_define
class SentinelToolCall:
    """
    Attributes:
        tool_id (str):
        type (SentinelToolCallType):
        id (Union[Unset, str]):
        name (Union[Unset, str]):
        arguments (Union[Unset, str]): Arguments in JSON format
    """

    tool_id: str
    type: SentinelToolCallType
    id: Union[Unset, str] = UNSET
    name: Union[Unset, str] = UNSET
    arguments: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        tool_id = self.tool_id

        type = self.type.value

        id = self.id

        name = self.name

        arguments = self.arguments

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "tool_id": tool_id,
                "type": type,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if arguments is not UNSET:
            field_dict["arguments"] = arguments

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        tool_id = d.pop("tool_id")

        type = SentinelToolCallType(d.pop("type"))

        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        arguments = d.pop("arguments", UNSET)

        sentinel_tool_call = cls(
            tool_id=tool_id,
            type=type,
            id=id,
            name=name,
            arguments=arguments,
        )

        sentinel_tool_call.additional_properties = d
        return sentinel_tool_call

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
