from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.asteroid_choice_finish_reason_type_1 import AsteroidChoiceFinishReasonType1

if TYPE_CHECKING:
    from ..models.asteroid_message import AsteroidMessage


T = TypeVar("T", bound="AsteroidChoice")


@_attrs_define
class AsteroidChoice:
    """
    Attributes:
        asteroid_id (str):
        index (int):
        message (AsteroidMessage):
        finish_reason (Union[AsteroidChoiceFinishReasonType1, None]):
    """

    asteroid_id: str
    index: int
    message: "AsteroidMessage"
    finish_reason: Union[AsteroidChoiceFinishReasonType1, None]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        asteroid_id = self.asteroid_id

        index = self.index

        message = self.message.to_dict()

        finish_reason: Union[None, str]
        if isinstance(self.finish_reason, AsteroidChoiceFinishReasonType1):
            finish_reason = self.finish_reason.value
        else:
            finish_reason = self.finish_reason

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "asteroid_id": asteroid_id,
                "index": index,
                "message": message,
                "finish_reason": finish_reason,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.asteroid_message import AsteroidMessage

        d = src_dict.copy()
        asteroid_id = d.pop("asteroid_id")

        index = d.pop("index")

        message = AsteroidMessage.from_dict(d.pop("message"))

        def _parse_finish_reason(data: object) -> Union[AsteroidChoiceFinishReasonType1, None]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                finish_reason_type_1 = AsteroidChoiceFinishReasonType1(data)

                return finish_reason_type_1
            except:  # noqa: E722
                pass
            return cast(Union[AsteroidChoiceFinishReasonType1, None], data)

        finish_reason = _parse_finish_reason(d.pop("finish_reason"))

        asteroid_choice = cls(
            asteroid_id=asteroid_id,
            index=index,
            message=message,
            finish_reason=finish_reason,
        )

        asteroid_choice.additional_properties = d
        return asteroid_choice

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
