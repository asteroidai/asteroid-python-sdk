import datetime
from typing import Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.decision import Decision
from ..types import UNSET, Unset

T = TypeVar("T", bound="ToolSupervisionResult")


@_attrs_define
class ToolSupervisionResult:
    """
    Attributes:
        id (UUID): The ID of the supervision result
        tool_id (UUID): The ID of the tool that the supervision result is for
        tool_call_id (UUID):
        supervisor_id (UUID): The ID of the supervisor that made the supervision result
        created_at (datetime.datetime): The timestamp of when the supervision result was created
        decision (Decision):
        reasoning (str): The reasoning behind the decision
        run_id (UUID): The ID of the run that the supervision result is for
        tool_name (Union[Unset, str]): The name of the tool that the supervision result is for
    """

    id: UUID
    tool_id: UUID
    tool_call_id: UUID
    supervisor_id: UUID
    created_at: datetime.datetime
    decision: Decision
    reasoning: str
    run_id: UUID
    tool_name: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        tool_id = str(self.tool_id)

        tool_call_id = str(self.tool_call_id)

        supervisor_id = str(self.supervisor_id)

        created_at = self.created_at.isoformat()

        decision = self.decision.value

        reasoning = self.reasoning

        run_id = str(self.run_id)

        tool_name = self.tool_name

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "tool_id": tool_id,
                "tool_call_id": tool_call_id,
                "supervisor_id": supervisor_id,
                "created_at": created_at,
                "decision": decision,
                "reasoning": reasoning,
                "run_id": run_id,
            }
        )
        if tool_name is not UNSET:
            field_dict["tool_name"] = tool_name

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = UUID(d.pop("id"))

        tool_id = UUID(d.pop("tool_id"))

        tool_call_id = UUID(d.pop("tool_call_id"))

        supervisor_id = UUID(d.pop("supervisor_id"))

        created_at = isoparse(d.pop("created_at"))

        decision = Decision(d.pop("decision"))

        reasoning = d.pop("reasoning")

        run_id = UUID(d.pop("run_id"))

        tool_name = d.pop("tool_name", UNSET)

        tool_supervision_result = cls(
            id=id,
            tool_id=tool_id,
            tool_call_id=tool_call_id,
            supervisor_id=supervisor_id,
            created_at=created_at,
            decision=decision,
            reasoning=reasoning,
            run_id=run_id,
            tool_name=tool_name,
        )

        tool_supervision_result.additional_properties = d
        return tool_supervision_result

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
