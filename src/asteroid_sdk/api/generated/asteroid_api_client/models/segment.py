from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.asteroid_message import AsteroidMessage
    from ..models.asteroid_tool_call import AsteroidToolCall


T = TypeVar("T", bound="Segment")


@_attrs_define
class Segment:
    """
    Attributes:
        message (AsteroidMessage):
        tool_calls (List['AsteroidToolCall']):
    """

    message: "AsteroidMessage"
    tool_calls: List["AsteroidToolCall"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        message = self.message.to_dict()

        tool_calls = []
        for tool_calls_item_data in self.tool_calls:
            tool_calls_item = tool_calls_item_data.to_dict()
            tool_calls.append(tool_calls_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "message": message,
                "tool_calls": tool_calls,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.asteroid_message import AsteroidMessage
        from ..models.asteroid_tool_call import AsteroidToolCall

        d = src_dict.copy()
        message = AsteroidMessage.from_dict(d.pop("message"))

        tool_calls = []
        _tool_calls = d.pop("tool_calls")
        for tool_calls_item_data in _tool_calls:
            tool_calls_item = AsteroidToolCall.from_dict(tool_calls_item_data)

            tool_calls.append(tool_calls_item)

        segment = cls(
            message=message,
            tool_calls=tool_calls,
        )

        segment.additional_properties = d
        return segment

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
