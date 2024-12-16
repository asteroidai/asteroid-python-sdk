import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.asteroid_message_role import AsteroidMessageRole
from ..models.message_type import MessageType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.asteroid_tool_call import AsteroidToolCall


T = TypeVar("T", bound="AsteroidMessage")


@_attrs_define
class AsteroidMessage:
    """
    Attributes:
        role (AsteroidMessageRole):
        content (str):
        id (Union[Unset, UUID]):
        tool_calls (Union[Unset, List['AsteroidToolCall']]):
        type (Union[Unset, MessageType]):
        created_at (Union[Unset, datetime.datetime]):
        data (Union[Unset, str]): The raw b64 encoded JSON of the message objects in its original form
    """

    role: AsteroidMessageRole
    content: str
    id: Union[Unset, UUID] = UNSET
    tool_calls: Union[Unset, List["AsteroidToolCall"]] = UNSET
    type: Union[Unset, MessageType] = UNSET
    created_at: Union[Unset, datetime.datetime] = UNSET
    data: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        role = self.role.value

        content = self.content

        id: Union[Unset, str] = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        tool_calls: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.tool_calls, Unset):
            tool_calls = []
            for tool_calls_item_data in self.tool_calls:
                tool_calls_item = tool_calls_item_data.to_dict()
                tool_calls.append(tool_calls_item)

        type: Union[Unset, str] = UNSET
        if not isinstance(self.type, Unset):
            type = self.type.value

        created_at: Union[Unset, str] = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        data = self.data

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "role": role,
                "content": content,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if tool_calls is not UNSET:
            field_dict["tool_calls"] = tool_calls
        if type is not UNSET:
            field_dict["type"] = type
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.asteroid_tool_call import AsteroidToolCall

        d = src_dict.copy()
        role = AsteroidMessageRole(d.pop("role"))

        content = d.pop("content")

        _id = d.pop("id", UNSET)
        id: Union[Unset, UUID]
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        tool_calls = []
        _tool_calls = d.pop("tool_calls", UNSET)
        for tool_calls_item_data in _tool_calls or []:
            tool_calls_item = AsteroidToolCall.from_dict(tool_calls_item_data)

            tool_calls.append(tool_calls_item)

        _type = d.pop("type", UNSET)
        type: Union[Unset, MessageType]
        if isinstance(_type, Unset):
            type = UNSET
        else:
            type = MessageType(_type)

        _created_at = d.pop("created_at", UNSET)
        created_at: Union[Unset, datetime.datetime]
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = isoparse(_created_at)

        data = d.pop("data", UNSET)

        asteroid_message = cls(
            role=role,
            content=content,
            id=id,
            tool_calls=tool_calls,
            type=type,
            created_at=created_at,
            data=data,
        )

        asteroid_message.additional_properties = d
        return asteroid_message

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
