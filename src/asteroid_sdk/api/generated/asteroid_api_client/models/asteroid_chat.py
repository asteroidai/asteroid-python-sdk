from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.chat_format import ChatFormat

T = TypeVar("T", bound="AsteroidChat")


@_attrs_define
class AsteroidChat:
    """The raw b64 encoded JSON of the request and response data sent/received from the LLM.

    Attributes:
        request_data (str):
        response_data (str):
        format_ (ChatFormat):
    """

    request_data: str
    response_data: str
    format_: ChatFormat
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        request_data = self.request_data

        response_data = self.response_data

        format_ = self.format_.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "request_data": request_data,
                "response_data": response_data,
                "format": format_,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        request_data = d.pop("request_data")

        response_data = d.pop("response_data")

        format_ = ChatFormat(d.pop("format"))

        asteroid_chat = cls(
            request_data=request_data,
            response_data=response_data,
            format_=format_,
        )

        asteroid_chat.additional_properties = d
        return asteroid_chat

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
