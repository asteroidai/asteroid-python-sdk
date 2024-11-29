from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.tool_call_arguments import ToolCallArguments


T = TypeVar("T", bound="ToolCall")


@_attrs_define
class ToolCall:
    """
    Attributes:
        id (str):
        function (str):
        arguments (ToolCallArguments):
        type (str):
        parse_error (Union[Unset, str]):
    """

    id: str
    function: str
    arguments: "ToolCallArguments"
    type: str
    parse_error: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        function = self.function

        arguments = self.arguments.to_dict()

        type = self.type

        parse_error = self.parse_error

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "function": function,
                "arguments": arguments,
                "type": type,
            }
        )
        if parse_error is not UNSET:
            field_dict["parse_error"] = parse_error

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.tool_call_arguments import ToolCallArguments

        d = src_dict.copy()
        id = d.pop("id")

        function = d.pop("function")

        arguments = ToolCallArguments.from_dict(d.pop("arguments"))

        type = d.pop("type")

        parse_error = d.pop("parse_error", UNSET)

        tool_call = cls(
            id=id,
            function=function,
            arguments=arguments,
            type=type,
            parse_error=parse_error,
        )

        tool_call.additional_properties = d
        return tool_call

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
