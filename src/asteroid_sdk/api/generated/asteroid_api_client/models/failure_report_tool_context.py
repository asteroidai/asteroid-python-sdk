from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.asteroid_tool_call import AsteroidToolCall


T = TypeVar("T", bound="FailureReportToolContext")


@_attrs_define
class FailureReportToolContext:
    """
    Attributes:
        tool_name (str):
        tool_call (AsteroidToolCall):
    """

    tool_name: str
    tool_call: "AsteroidToolCall"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        tool_name = self.tool_name

        tool_call = self.tool_call.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "tool_name": tool_name,
                "tool_call": tool_call,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.asteroid_tool_call import AsteroidToolCall

        d = src_dict.copy()
        tool_name = d.pop("tool_name")

        tool_call = AsteroidToolCall.from_dict(d.pop("tool_call"))

        failure_report_tool_context = cls(
            tool_name=tool_name,
            tool_call=tool_call,
        )

        failure_report_tool_context.additional_properties = d
        return failure_report_tool_context

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
