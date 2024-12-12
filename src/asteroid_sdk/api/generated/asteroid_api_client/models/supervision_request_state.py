from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.supervision_request import SupervisionRequest
    from ..models.supervision_result import SupervisionResult
    from ..models.supervision_status import SupervisionStatus


T = TypeVar("T", bound="SupervisionRequestState")


@_attrs_define
class SupervisionRequestState:
    """
    Attributes:
        supervision_request (SupervisionRequest):
        status (SupervisionStatus):
        result (Union[Unset, SupervisionResult]):
    """

    supervision_request: "SupervisionRequest"
    status: "SupervisionStatus"
    result: Union[Unset, "SupervisionResult"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        supervision_request = self.supervision_request.to_dict()

        status = self.status.to_dict()

        result: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.result, Unset):
            result = self.result.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "supervision_request": supervision_request,
                "status": status,
            }
        )
        if result is not UNSET:
            field_dict["result"] = result

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.supervision_request import SupervisionRequest
        from ..models.supervision_result import SupervisionResult
        from ..models.supervision_status import SupervisionStatus

        d = src_dict.copy()
        supervision_request = SupervisionRequest.from_dict(d.pop("supervision_request"))

        status = SupervisionStatus.from_dict(d.pop("status"))

        _result = d.pop("result", UNSET)
        result: Union[Unset, SupervisionResult]
        if isinstance(_result, Unset):
            result = UNSET
        else:
            result = SupervisionResult.from_dict(_result)

        supervision_request_state = cls(
            supervision_request=supervision_request,
            status=status,
            result=result,
        )

        supervision_request_state.additional_properties = d
        return supervision_request_state

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
