from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ToolCallIds")


@_attrs_define
class ToolCallIds:
    """
    Attributes:
        tool_call_id (Union[Unset, str]):
        tool_id (Union[Unset, str]):
    """

    tool_call_id: Union[Unset, str] = UNSET
    tool_id: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        tool_call_id = self.tool_call_id

        tool_id = self.tool_id

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if tool_call_id is not UNSET:
            field_dict["tool_call_id"] = tool_call_id
        if tool_id is not UNSET:
            field_dict["tool_id"] = tool_id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        tool_call_id = d.pop("tool_call_id", UNSET)

        tool_id = d.pop("tool_id", UNSET)

        tool_call_ids = cls(
            tool_call_id=tool_call_id,
            tool_id=tool_id,
        )

        tool_call_ids.additional_properties = d
        return tool_call_ids

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
