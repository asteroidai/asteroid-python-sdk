from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AgentReportRunStatistics")


@_attrs_define
class AgentReportRunStatistics:
    """
    Attributes:
        successful_runs (Union[Unset, int]):
        failed_runs (Union[Unset, int]):
        pending_runs (Union[Unset, int]):
        average_run_duration (Union[Unset, float]): Average duration of runs in seconds
    """

    successful_runs: Union[Unset, int] = UNSET
    failed_runs: Union[Unset, int] = UNSET
    pending_runs: Union[Unset, int] = UNSET
    average_run_duration: Union[Unset, float] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        successful_runs = self.successful_runs

        failed_runs = self.failed_runs

        pending_runs = self.pending_runs

        average_run_duration = self.average_run_duration

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if successful_runs is not UNSET:
            field_dict["successful_runs"] = successful_runs
        if failed_runs is not UNSET:
            field_dict["failed_runs"] = failed_runs
        if pending_runs is not UNSET:
            field_dict["pending_runs"] = pending_runs
        if average_run_duration is not UNSET:
            field_dict["average_run_duration"] = average_run_duration

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        successful_runs = d.pop("successful_runs", UNSET)

        failed_runs = d.pop("failed_runs", UNSET)

        pending_runs = d.pop("pending_runs", UNSET)

        average_run_duration = d.pop("average_run_duration", UNSET)

        agent_report_run_statistics = cls(
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            pending_runs=pending_runs,
            average_run_duration=average_run_duration,
        )

        agent_report_run_statistics.additional_properties = d
        return agent_report_run_statistics

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
