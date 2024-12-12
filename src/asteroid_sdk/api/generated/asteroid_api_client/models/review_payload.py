from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.chain_execution_state import ChainExecutionState
    from ..models.supervision_request import SupervisionRequest
    from ..models.tool_call import ToolCall


T = TypeVar("T", bound="ReviewPayload")


@_attrs_define
class ReviewPayload:
    """Contains all the information needed for a human reviewer to make a supervision decision

    Attributes:
        supervision_request (SupervisionRequest):
        chain_state (ChainExecutionState):
        run_id (UUID): The ID of the run this review is for
        toolcall (Union[Unset, ToolCall]):
    """

    supervision_request: "SupervisionRequest"
    chain_state: "ChainExecutionState"
    run_id: UUID
    toolcall: Union[Unset, "ToolCall"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        supervision_request = self.supervision_request.to_dict()

        chain_state = self.chain_state.to_dict()

        run_id = str(self.run_id)

        toolcall: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.toolcall, Unset):
            toolcall = self.toolcall.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "supervision_request": supervision_request,
                "chain_state": chain_state,
                "run_id": run_id,
            }
        )
        if toolcall is not UNSET:
            field_dict["toolcall"] = toolcall

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.chain_execution_state import ChainExecutionState
        from ..models.supervision_request import SupervisionRequest
        from ..models.tool_call import ToolCall

        d = src_dict.copy()
        supervision_request = SupervisionRequest.from_dict(d.pop("supervision_request"))

        chain_state = ChainExecutionState.from_dict(d.pop("chain_state"))

        run_id = UUID(d.pop("run_id"))

        _toolcall = d.pop("toolcall", UNSET)
        toolcall: Union[Unset, ToolCall]
        if isinstance(_toolcall, Unset):
            toolcall = UNSET
        else:
            toolcall = ToolCall.from_dict(_toolcall)

        review_payload = cls(
            supervision_request=supervision_request,
            chain_state=chain_state,
            run_id=run_id,
            toolcall=toolcall,
        )

        review_payload.additional_properties = d
        return review_payload

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
