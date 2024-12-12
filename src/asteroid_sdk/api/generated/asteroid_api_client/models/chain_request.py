from typing import Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ChainRequest")


@_attrs_define
class ChainRequest:
    """
    Attributes:
        supervisor_ids (Union[Unset, List[UUID]]): Array of supervisor IDs to create chains with
    """

    supervisor_ids: Union[Unset, List[UUID]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        supervisor_ids: Union[Unset, List[str]] = UNSET
        if not isinstance(self.supervisor_ids, Unset):
            supervisor_ids = []
            for supervisor_ids_item_data in self.supervisor_ids:
                supervisor_ids_item = str(supervisor_ids_item_data)
                supervisor_ids.append(supervisor_ids_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if supervisor_ids is not UNSET:
            field_dict["supervisor_ids"] = supervisor_ids

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        supervisor_ids = []
        _supervisor_ids = d.pop("supervisor_ids", UNSET)
        for supervisor_ids_item_data in _supervisor_ids or []:
            supervisor_ids_item = UUID(supervisor_ids_item_data)

            supervisor_ids.append(supervisor_ids_item)

        chain_request = cls(
            supervisor_ids=supervisor_ids,
        )

        chain_request.additional_properties = d
        return chain_request

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
