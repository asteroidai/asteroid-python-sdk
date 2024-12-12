from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.chain_execution import ChainExecution
    from ..models.supervision_request_state import SupervisionRequestState
    from ..models.supervisor_chain import SupervisorChain


T = TypeVar("T", bound="ChainExecutionState")


@_attrs_define
class ChainExecutionState:
    """
    Attributes:
        chain (SupervisorChain):
        chain_execution (ChainExecution):
        supervision_requests (List['SupervisionRequestState']):
    """

    chain: "SupervisorChain"
    chain_execution: "ChainExecution"
    supervision_requests: List["SupervisionRequestState"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        chain = self.chain.to_dict()

        chain_execution = self.chain_execution.to_dict()

        supervision_requests = []
        for supervision_requests_item_data in self.supervision_requests:
            supervision_requests_item = supervision_requests_item_data.to_dict()
            supervision_requests.append(supervision_requests_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chain": chain,
                "chain_execution": chain_execution,
                "supervision_requests": supervision_requests,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.chain_execution import ChainExecution
        from ..models.supervision_request_state import SupervisionRequestState
        from ..models.supervisor_chain import SupervisorChain

        d = src_dict.copy()
        chain = SupervisorChain.from_dict(d.pop("chain"))

        chain_execution = ChainExecution.from_dict(d.pop("chain_execution"))

        supervision_requests = []
        _supervision_requests = d.pop("supervision_requests")
        for supervision_requests_item_data in _supervision_requests:
            supervision_requests_item = SupervisionRequestState.from_dict(supervision_requests_item_data)

            supervision_requests.append(supervision_requests_item)

        chain_execution_state = cls(
            chain=chain,
            chain_execution=chain_execution,
            supervision_requests=supervision_requests,
        )

        chain_execution_state.additional_properties = d
        return chain_execution_state

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
