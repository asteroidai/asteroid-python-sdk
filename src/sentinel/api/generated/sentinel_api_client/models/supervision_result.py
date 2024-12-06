import datetime
from typing import Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.decision import Decision
from ..types import UNSET, Unset

T = TypeVar("T", bound="SupervisionResult")


@_attrs_define
class SupervisionResult:
    """
    Attributes:
        supervision_request_id (UUID):
        created_at (datetime.datetime):
        decision (Decision):
        reasoning (str):
        id (Union[Unset, UUID]):
        toolcall_id (Union[Unset, UUID]):
    """

    supervision_request_id: UUID
    created_at: datetime.datetime
    decision: Decision
    reasoning: str
    id: Union[Unset, UUID] = UNSET
    toolcall_id: Union[Unset, UUID] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        supervision_request_id = str(self.supervision_request_id)

        created_at = self.created_at.isoformat()

        decision = self.decision.value

        reasoning = self.reasoning

        id: Union[Unset, str] = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        toolcall_id: Union[Unset, str] = UNSET
        if not isinstance(self.toolcall_id, Unset):
            toolcall_id = str(self.toolcall_id)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "supervision_request_id": supervision_request_id,
                "created_at": created_at,
                "decision": decision,
                "reasoning": reasoning,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if toolcall_id is not UNSET:
            field_dict["toolcall_id"] = toolcall_id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        supervision_request_id = UUID(d.pop("supervision_request_id"))

        created_at = isoparse(d.pop("created_at"))

        decision = Decision(d.pop("decision"))

        reasoning = d.pop("reasoning")

        _id = d.pop("id", UNSET)
        id: Union[Unset, UUID]
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        _toolcall_id = d.pop("toolcall_id", UNSET)
        toolcall_id: Union[Unset, UUID]
        if isinstance(_toolcall_id, Unset):
            toolcall_id = UNSET
        else:
            toolcall_id = UUID(_toolcall_id)

        supervision_result = cls(
            supervision_request_id=supervision_request_id,
            created_at=created_at,
            decision=decision,
            reasoning=reasoning,
            id=id,
            toolcall_id=toolcall_id,
        )

        supervision_result.additional_properties = d
        return supervision_result

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
