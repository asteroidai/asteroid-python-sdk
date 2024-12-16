import datetime
from typing import Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="AsteroidToolCall")


@_attrs_define
class AsteroidToolCall:
    """
    Attributes:
        id (UUID):
        tool_id (UUID):
        call_id (Union[Unset, str]):
        name (Union[Unset, str]):
        arguments (Union[Unset, str]): Arguments in JSON format
        created_at (Union[Unset, datetime.datetime]):
    """

    id: UUID
    tool_id: UUID
    call_id: Union[Unset, str] = UNSET
    name: Union[Unset, str] = UNSET
    arguments: Union[Unset, str] = UNSET
    created_at: Union[Unset, datetime.datetime] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        tool_id = str(self.tool_id)

        call_id = self.call_id

        name = self.name

        arguments = self.arguments

        created_at: Union[Unset, str] = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "tool_id": tool_id,
            }
        )
        if call_id is not UNSET:
            field_dict["call_id"] = call_id
        if name is not UNSET:
            field_dict["name"] = name
        if arguments is not UNSET:
            field_dict["arguments"] = arguments
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = UUID(d.pop("id"))

        tool_id = UUID(d.pop("tool_id"))

        call_id = d.pop("call_id", UNSET)

        name = d.pop("name", UNSET)

        arguments = d.pop("arguments", UNSET)

        _created_at = d.pop("created_at", UNSET)
        created_at: Union[Unset, datetime.datetime]
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = isoparse(_created_at)

        asteroid_tool_call = cls(
            id=id,
            tool_id=tool_id,
            call_id=call_id,
            name=name,
            arguments=arguments,
            created_at=created_at,
        )

        asteroid_tool_call.additional_properties = d
        return asteroid_tool_call

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
