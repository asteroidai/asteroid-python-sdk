from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.choice_ids import ChoiceIds


T = TypeVar("T", bound="ChatIds")


@_attrs_define
class ChatIds:
    """
    Attributes:
        chat_id (UUID):
        choice_ids (List['ChoiceIds']):
    """

    chat_id: UUID
    choice_ids: List["ChoiceIds"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        chat_id = str(self.chat_id)

        choice_ids = []
        for choice_ids_item_data in self.choice_ids:
            choice_ids_item = choice_ids_item_data.to_dict()
            choice_ids.append(choice_ids_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chat_id": chat_id,
                "choice_ids": choice_ids,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.choice_ids import ChoiceIds

        d = src_dict.copy()
        chat_id = UUID(d.pop("chat_id"))

        choice_ids = []
        _choice_ids = d.pop("choice_ids")
        for choice_ids_item_data in _choice_ids:
            choice_ids_item = ChoiceIds.from_dict(choice_ids_item_data)

            choice_ids.append(choice_ids_item)

        chat_ids = cls(
            chat_id=chat_id,
            choice_ids=choice_ids,
        )

        chat_ids.additional_properties = d
        return chat_ids

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
