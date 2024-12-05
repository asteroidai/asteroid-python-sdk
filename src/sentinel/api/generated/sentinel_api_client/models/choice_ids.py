from typing import Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ChoiceIds")


@_attrs_define
class ChoiceIds:
    """
    Attributes:
        choice_id (str):
        message_id (str):
        tool_call_ids (List[str]):
    """

    choice_id: str
    message_id: str
    tool_call_ids: List[str]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        choice_id = self.choice_id

        message_id = self.message_id

        tool_call_ids = self.tool_call_ids

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "choice_id": choice_id,
                "message_id": message_id,
                "tool_call_ids": tool_call_ids,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        choice_id = d.pop("choice_id")

        message_id = d.pop("message_id")

        tool_call_ids = cast(List[str], d.pop("tool_call_ids"))

        choice_ids = cls(
            choice_id=choice_id,
            message_id=message_id,
            tool_call_ids=tool_call_ids,
        )

        choice_ids.additional_properties = d
        return choice_ids

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
