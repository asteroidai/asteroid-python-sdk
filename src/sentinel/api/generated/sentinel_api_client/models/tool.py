from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.tool_attributes import ToolAttributes


T = TypeVar("T", bound="Tool")


@_attrs_define
class Tool:
    """
    Attributes:
        run_id (UUID):
        name (str):
        description (str):
        attributes (ToolAttributes):
        code (str):
        id (Union[Unset, UUID]):
        ignored_attributes (Union[Unset, List[str]]):
    """

    run_id: UUID
    name: str
    description: str
    attributes: "ToolAttributes"
    code: str
    id: Union[Unset, UUID] = UNSET
    ignored_attributes: Union[Unset, List[str]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        run_id = str(self.run_id)

        name = self.name

        description = self.description

        attributes = self.attributes.to_dict()

        code = self.code

        id: Union[Unset, str] = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        ignored_attributes: Union[Unset, List[str]] = UNSET
        if not isinstance(self.ignored_attributes, Unset):
            ignored_attributes = self.ignored_attributes

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "run_id": run_id,
                "name": name,
                "description": description,
                "attributes": attributes,
                "code": code,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if ignored_attributes is not UNSET:
            field_dict["ignored_attributes"] = ignored_attributes

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.tool_attributes import ToolAttributes

        d = src_dict.copy()
        run_id = UUID(d.pop("run_id"))

        name = d.pop("name")

        description = d.pop("description")

        attributes = ToolAttributes.from_dict(d.pop("attributes"))

        code = d.pop("code")

        _id = d.pop("id", UNSET)
        id: Union[Unset, UUID]
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        ignored_attributes = cast(List[str], d.pop("ignored_attributes", UNSET))

        tool = cls(
            run_id=run_id,
            name=name,
            description=description,
            attributes=attributes,
            code=code,
            id=id,
            ignored_attributes=ignored_attributes,
        )

        tool.additional_properties = d
        return tool

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
