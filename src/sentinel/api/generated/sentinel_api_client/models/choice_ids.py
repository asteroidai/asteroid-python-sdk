from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.tool_call_ids import ToolCallIds


T = TypeVar("T", bound="ChoiceIds")


@_attrs_define
class ChoiceIds:
    """
    Attributes:
        choice_id (str):
        message_id (str):
        tool_call_ids (List['ToolCallIds']):
    """

    choice_id: str
    message_id: str
    tool_call_ids: List["ToolCallIds"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        choice_id = self.choice_id

        message_id = self.message_id

        tool_call_ids = []
        for tool_call_ids_item_data in self.tool_call_ids:
            tool_call_ids_item = tool_call_ids_item_data.to_dict()
            tool_call_ids.append(tool_call_ids_item)

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
        from ..models.tool_call_ids import ToolCallIds

        d = src_dict.copy()
        choice_id = d.pop("choice_id")

        message_id = d.pop("message_id")

        tool_call_ids = []
        _tool_call_ids = d.pop("tool_call_ids")
        for tool_call_ids_item_data in _tool_call_ids:
            tool_call_ids_item = ToolCallIds.from_dict(tool_call_ids_item_data)

            tool_call_ids.append(tool_call_ids_item)

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
