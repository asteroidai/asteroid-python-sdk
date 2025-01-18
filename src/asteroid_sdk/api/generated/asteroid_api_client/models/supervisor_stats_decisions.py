from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="SupervisorStatsDecisions")


@_attrs_define
class SupervisorStatsDecisions:
    """
    Attributes:
        approve (int):
        reject (int):
        terminate (int):
        modify (int):
        escalate (int):
    """

    approve: int
    reject: int
    terminate: int
    modify: int
    escalate: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        approve = self.approve

        reject = self.reject

        terminate = self.terminate

        modify = self.modify

        escalate = self.escalate

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "approve": approve,
                "reject": reject,
                "terminate": terminate,
                "modify": modify,
                "escalate": escalate,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        approve = d.pop("approve")

        reject = d.pop("reject")

        terminate = d.pop("terminate")

        modify = d.pop("modify")

        escalate = d.pop("escalate")

        supervisor_stats_decisions = cls(
            approve=approve,
            reject=reject,
            terminate=terminate,
            modify=modify,
            escalate=escalate,
        )

        supervisor_stats_decisions.additional_properties = d
        return supervisor_stats_decisions

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
