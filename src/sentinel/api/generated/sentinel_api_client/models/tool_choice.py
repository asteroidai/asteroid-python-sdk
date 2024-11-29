from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.arguments import Arguments


T = TypeVar("T", bound="ToolChoice")


@_attrs_define
class ToolChoice:
    """
    Attributes:
        id (str):
        function (str):
        arguments (Arguments):
        type (str):
    """

    id: str
    function: str
    arguments: "Arguments"
    type: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        function = self.function

        arguments = self.arguments.to_dict()

        type = self.type

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

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.arguments import Arguments

        d = src_dict.copy()
        id = d.pop("id")

        function = d.pop("function")

        arguments = Arguments.from_dict(d.pop("arguments"))

        type = d.pop("type")

        tool_choice = cls(
            id=id,
            function=function,
            arguments=arguments,
            type=type,
        )

        tool_choice.additional_properties = d
        return tool_choice

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
