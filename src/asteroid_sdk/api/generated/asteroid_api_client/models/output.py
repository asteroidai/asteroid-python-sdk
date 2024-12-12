from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.choice import Choice
    from ..models.usage import Usage


T = TypeVar("T", bound="Output")


@_attrs_define
class Output:
    """
    Attributes:
        model (Union[Unset, str]):
        choices (Union[Unset, List['Choice']]):
        usage (Union[Unset, Usage]):
    """

    model: Union[Unset, str] = UNSET
    choices: Union[Unset, List["Choice"]] = UNSET
    usage: Union[Unset, "Usage"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        model = self.model

        choices: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.choices, Unset):
            choices = []
            for choices_item_data in self.choices:
                choices_item = choices_item_data.to_dict()
                choices.append(choices_item)

        usage: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.usage, Unset):
            usage = self.usage.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if model is not UNSET:
            field_dict["model"] = model
        if choices is not UNSET:
            field_dict["choices"] = choices
        if usage is not UNSET:
            field_dict["usage"] = usage

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.choice import Choice
        from ..models.usage import Usage

        d = src_dict.copy()
        model = d.pop("model", UNSET)

        choices = []
        _choices = d.pop("choices", UNSET)
        for choices_item_data in _choices or []:
            choices_item = Choice.from_dict(choices_item_data)

            choices.append(choices_item)

        _usage = d.pop("usage", UNSET)
        usage: Union[Unset, Usage]
        if isinstance(_usage, Unset):
            usage = UNSET
        else:
            usage = Usage.from_dict(_usage)

        output = cls(
            model=model,
            choices=choices,
            usage=usage,
        )

        output.additional_properties = d
        return output

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
