import datetime
from typing import Any, Dict, List, Type, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="ChainExecution")


@_attrs_define
class ChainExecution:
    """
    Attributes:
        id (UUID):
        request_group_id (UUID):
        chain_id (UUID):
        created_at (datetime.datetime):
    """

    id: UUID
    request_group_id: UUID
    chain_id: UUID
    created_at: datetime.datetime
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        request_group_id = str(self.request_group_id)

        chain_id = str(self.chain_id)

        created_at = self.created_at.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "request_group_id": request_group_id,
                "chain_id": chain_id,
                "created_at": created_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = UUID(d.pop("id"))

        request_group_id = UUID(d.pop("request_group_id"))

        chain_id = UUID(d.pop("chain_id"))

        created_at = isoparse(d.pop("created_at"))

        chain_execution = cls(
            id=id,
            request_group_id=request_group_id,
            chain_id=chain_id,
            created_at=created_at,
        )

        chain_execution.additional_properties = d
        return chain_execution

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
