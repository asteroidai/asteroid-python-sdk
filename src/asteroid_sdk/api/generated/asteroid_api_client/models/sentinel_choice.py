from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.sentinel_choice_finish_reason_type_1 import SentinelChoiceFinishReasonType1

if TYPE_CHECKING:
    from ..models.sentinel_message import SentinelMessage


T = TypeVar("T", bound="SentinelChoice")


@_attrs_define
class SentinelChoice:
    """
    Attributes:
        sentinel_id (str):
        index (int):
        message (SentinelMessage):
        finish_reason (Union[None, SentinelChoiceFinishReasonType1]):
    """

    sentinel_id: str
    index: int
    message: "SentinelMessage"
    finish_reason: Union[None, SentinelChoiceFinishReasonType1]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        sentinel_id = self.sentinel_id

        index = self.index

        message = self.message.to_dict()

        finish_reason: Union[None, str]
        if isinstance(self.finish_reason, SentinelChoiceFinishReasonType1):
            finish_reason = self.finish_reason.value
        else:
            finish_reason = self.finish_reason

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "sentinel_id": sentinel_id,
                "index": index,
                "message": message,
                "finish_reason": finish_reason,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.sentinel_message import SentinelMessage

        d = src_dict.copy()
        sentinel_id = d.pop("sentinel_id")

        index = d.pop("index")

        message = SentinelMessage.from_dict(d.pop("message"))

        def _parse_finish_reason(data: object) -> Union[None, SentinelChoiceFinishReasonType1]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                finish_reason_type_1 = SentinelChoiceFinishReasonType1(data)

                return finish_reason_type_1
            except:  # noqa: E722
                pass
            return cast(Union[None, SentinelChoiceFinishReasonType1], data)

        finish_reason = _parse_finish_reason(d.pop("finish_reason"))

        sentinel_choice = cls(
            sentinel_id=sentinel_id,
            index=index,
            message=message,
            finish_reason=finish_reason,
        )

        sentinel_choice.additional_properties = d
        return sentinel_choice

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
