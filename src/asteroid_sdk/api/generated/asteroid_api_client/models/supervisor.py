import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.supervisor_type import SupervisorType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.supervisor_attributes import SupervisorAttributes


T = TypeVar("T", bound="Supervisor")


@_attrs_define
class Supervisor:
    """
    Attributes:
        name (str):
        description (str):
        created_at (datetime.datetime):
        type (SupervisorType): The type of supervisor. ClientSupervisor means that the supervision is done client side
            and the server is merely informed. Other supervisor types are handled serverside, e.g. HumanSupervisor means
            that a human will review the request via the Sentinel UI.
        code (str):
        attributes (SupervisorAttributes):
        id (Union[Unset, UUID]):
    """

    name: str
    description: str
    created_at: datetime.datetime
    type: SupervisorType
    code: str
    attributes: "SupervisorAttributes"
    id: Union[Unset, UUID] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        description = self.description

        created_at = self.created_at.isoformat()

        type = self.type.value

        code = self.code

        attributes = self.attributes.to_dict()

        id: Union[Unset, str] = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "description": description,
                "created_at": created_at,
                "type": type,
                "code": code,
                "attributes": attributes,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.supervisor_attributes import SupervisorAttributes

        d = src_dict.copy()
        name = d.pop("name")

        description = d.pop("description")

        created_at = isoparse(d.pop("created_at"))

        type = SupervisorType(d.pop("type"))

        code = d.pop("code")

        attributes = SupervisorAttributes.from_dict(d.pop("attributes"))

        _id = d.pop("id", UNSET)
        id: Union[Unset, UUID]
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        supervisor = cls(
            name=name,
            description=description,
            created_at=created_at,
            type=type,
            code=code,
            attributes=attributes,
            id=id,
        )

        supervisor.additional_properties = d
        return supervisor

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
