from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_run_tool_body_attributes import CreateRunToolBodyAttributes


T = TypeVar("T", bound="CreateRunToolBody")


@_attrs_define
class CreateRunToolBody:
    """
    Attributes:
        name (str):
        description (str):
        attributes (CreateRunToolBodyAttributes):
        code (str):
        ignored_attributes (Union[Unset, List[str]]):
    """

    name: str
    description: str
    attributes: "CreateRunToolBodyAttributes"
    code: str
    ignored_attributes: Union[Unset, List[str]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        description = self.description

        attributes = self.attributes.to_dict()

        code = self.code

        ignored_attributes: Union[Unset, List[str]] = UNSET
        if not isinstance(self.ignored_attributes, Unset):
            ignored_attributes = self.ignored_attributes

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "description": description,
                "attributes": attributes,
                "code": code,
            }
        )
        if ignored_attributes is not UNSET:
            field_dict["ignored_attributes"] = ignored_attributes

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.create_run_tool_body_attributes import CreateRunToolBodyAttributes

        d = src_dict.copy()
        name = d.pop("name")

        description = d.pop("description")

        attributes = CreateRunToolBodyAttributes.from_dict(d.pop("attributes"))

        code = d.pop("code")

        ignored_attributes = cast(List[str], d.pop("ignored_attributes", UNSET))

        create_run_tool_body = cls(
            name=name,
            description=description,
            attributes=attributes,
            code=code,
            ignored_attributes=ignored_attributes,
        )

        create_run_tool_body.additional_properties = d
        return create_run_tool_body

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
