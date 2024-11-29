from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.chain_execution_state import ChainExecutionState
    from ..models.supervision_request import SupervisionRequest
    from ..models.tool_request_group import ToolRequestGroup


T = TypeVar("T", bound="ReviewPayload")


@_attrs_define
class ReviewPayload:
    """Contains all the information needed for a human reviewer to make a supervision decision

    Attributes:
        supervision_request (SupervisionRequest):
        chain_state (ChainExecutionState):
        request_group (ToolRequestGroup):
        run_id (UUID): The ID of the run this review is for
    """

    supervision_request: "SupervisionRequest"
    chain_state: "ChainExecutionState"
    request_group: "ToolRequestGroup"
    run_id: UUID
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        supervision_request = self.supervision_request.to_dict()

        chain_state = self.chain_state.to_dict()

        request_group = self.request_group.to_dict()

        run_id = str(self.run_id)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "supervision_request": supervision_request,
                "chain_state": chain_state,
                "request_group": request_group,
                "run_id": run_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.chain_execution_state import ChainExecutionState
        from ..models.supervision_request import SupervisionRequest
        from ..models.tool_request_group import ToolRequestGroup

        d = src_dict.copy()
        supervision_request = SupervisionRequest.from_dict(d.pop("supervision_request"))

        chain_state = ChainExecutionState.from_dict(d.pop("chain_state"))

        request_group = ToolRequestGroup.from_dict(d.pop("request_group"))

        run_id = UUID(d.pop("run_id"))

        review_payload = cls(
            supervision_request=supervision_request,
            chain_state=chain_state,
            request_group=request_group,
            run_id=run_id,
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
