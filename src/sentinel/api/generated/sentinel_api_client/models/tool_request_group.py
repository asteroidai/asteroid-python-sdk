import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.tool_request import ToolRequest


T = TypeVar("T", bound="ToolRequestGroup")


@_attrs_define
class ToolRequestGroup:
    """
    Attributes:
        tool_requests (List['ToolRequest']):
        id (Union[Unset, UUID]):
        created_at (Union[Unset, datetime.datetime]):
    """

    tool_requests: List["ToolRequest"]
    id: Union[Unset, UUID] = UNSET
    created_at: Union[Unset, datetime.datetime] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        tool_requests = []
        for tool_requests_item_data in self.tool_requests:
            tool_requests_item = tool_requests_item_data.to_dict()
            tool_requests.append(tool_requests_item)

        id: Union[Unset, str] = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        created_at: Union[Unset, str] = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "tool_requests": tool_requests,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.tool_request import ToolRequest

        d = src_dict.copy()
        tool_requests = []
        _tool_requests = d.pop("tool_requests")
        for tool_requests_item_data in _tool_requests:
            tool_requests_item = ToolRequest.from_dict(tool_requests_item_data)

            tool_requests.append(tool_requests_item)

        _id = d.pop("id", UNSET)
        id: Union[Unset, UUID]
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        _created_at = d.pop("created_at", UNSET)
        created_at: Union[Unset, datetime.datetime]
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = isoparse(_created_at)

        tool_request_group = cls(
            tool_requests=tool_requests,
            id=id,
            created_at=created_at,
        )

        tool_request_group.additional_properties = d
        return tool_request_group

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
