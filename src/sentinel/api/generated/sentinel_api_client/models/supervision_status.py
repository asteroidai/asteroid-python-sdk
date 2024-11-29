import datetime
from typing import Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.status import Status
from ..types import UNSET, Unset

T = TypeVar("T", bound="SupervisionStatus")


@_attrs_define
class SupervisionStatus:
    """
    Attributes:
        id (int):
        status (Status):
        created_at (datetime.datetime):
        supervision_request_id (Union[Unset, UUID]):
    """

    id: int
    status: Status
    created_at: datetime.datetime
    supervision_request_id: Union[Unset, UUID] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        status = self.status.value

        created_at = self.created_at.isoformat()

        supervision_request_id: Union[Unset, str] = UNSET
        if not isinstance(self.supervision_request_id, Unset):
            supervision_request_id = str(self.supervision_request_id)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "status": status,
                "created_at": created_at,
            }
        )
        if supervision_request_id is not UNSET:
            field_dict["supervision_request_id"] = supervision_request_id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = d.pop("id")

        status = Status(d.pop("status"))

        created_at = isoparse(d.pop("created_at"))

        _supervision_request_id = d.pop("supervision_request_id", UNSET)
        supervision_request_id: Union[Unset, UUID]
        if isinstance(_supervision_request_id, Unset):
            supervision_request_id = UNSET
        else:
            supervision_request_id = UUID(_supervision_request_id)

        supervision_status = cls(
            id=id,
            status=status,
            created_at=created_at,
            supervision_request_id=supervision_request_id,
        )

        supervision_status.additional_properties = d
        return supervision_status

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
