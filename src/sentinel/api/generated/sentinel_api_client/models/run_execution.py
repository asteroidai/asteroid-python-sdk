from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.status import Status

if TYPE_CHECKING:
    from ..models.chain_execution_state import ChainExecutionState
    from ..models.tool_request_group import ToolRequestGroup


T = TypeVar("T", bound="RunExecution")


@_attrs_define
class RunExecution:
    """
    Attributes:
        request_group (ToolRequestGroup):
        chains (List['ChainExecutionState']):
        status (Status):
    """

    request_group: "ToolRequestGroup"
    chains: List["ChainExecutionState"]
    status: Status
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        request_group = self.request_group.to_dict()

        chains = []
        for chains_item_data in self.chains:
            chains_item = chains_item_data.to_dict()
            chains.append(chains_item)

        status = self.status.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "request_group": request_group,
                "chains": chains,
                "status": status,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.chain_execution_state import ChainExecutionState
        from ..models.tool_request_group import ToolRequestGroup

        d = src_dict.copy()
        request_group = ToolRequestGroup.from_dict(d.pop("request_group"))

        chains = []
        _chains = d.pop("chains")
        for chains_item_data in _chains:
            chains_item = ChainExecutionState.from_dict(chains_item_data)

            chains.append(chains_item)

        status = Status(d.pop("status"))

        run_execution = cls(
            request_group=request_group,
            chains=chains,
            status=status,
        )

        run_execution.additional_properties = d
        return run_execution

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
