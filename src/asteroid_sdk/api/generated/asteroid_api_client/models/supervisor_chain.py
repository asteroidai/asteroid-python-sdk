from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.supervisor import Supervisor


T = TypeVar("T", bound="SupervisorChain")


@_attrs_define
class SupervisorChain:
    """
    Attributes:
        chain_id (UUID):
        supervisors (List['Supervisor']):
    """

    chain_id: UUID
    supervisors: List["Supervisor"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        chain_id = str(self.chain_id)

        supervisors = []
        for supervisors_item_data in self.supervisors:
            supervisors_item = supervisors_item_data.to_dict()
            supervisors.append(supervisors_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chain_id": chain_id,
                "supervisors": supervisors,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.supervisor import Supervisor

        d = src_dict.copy()
        chain_id = UUID(d.pop("chain_id"))

        supervisors = []
        _supervisors = d.pop("supervisors")
        for supervisors_item_data in _supervisors:
            supervisors_item = Supervisor.from_dict(supervisors_item_data)

            supervisors.append(supervisors_item)

        supervisor_chain = cls(
            chain_id=chain_id,
            supervisors=supervisors,
        )

        supervisor_chain.additional_properties = d
        return supervisor_chain

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
