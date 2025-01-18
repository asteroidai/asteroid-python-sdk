from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.agent_report_failure_categories import AgentReportFailureCategories
    from ..models.agent_report_run_statistics import AgentReportRunStatistics
    from ..models.agent_report_supervisor_statistics import AgentReportSupervisorStatistics
    from ..models.agent_report_time_period import AgentReportTimePeriod
    from ..models.failure_report import FailureReport


T = TypeVar("T", bound="AgentReport")


@_attrs_define
class AgentReport:
    """A comprehensive report on an agent's performance across multiple runs

    Attributes:
        agent_id (UUID): Unique identifier for the agent
        total_runs (int): Total number of runs performed by the agent
        success_rate (float): Percentage of successful runs (0-100)
        run_statistics (AgentReportRunStatistics):
        failure_analysis (List['FailureReport']):
        failure_categories (AgentReportFailureCategories): Map of failure categories to their occurrence count
        supervisor_statistics (AgentReportSupervisorStatistics):
        time_period (AgentReportTimePeriod):
        prompt_text (Union[Unset, str]): The text of the prompt used by the agent
    """

    agent_id: UUID
    total_runs: int
    success_rate: float
    run_statistics: "AgentReportRunStatistics"
    failure_analysis: List["FailureReport"]
    failure_categories: "AgentReportFailureCategories"
    supervisor_statistics: "AgentReportSupervisorStatistics"
    time_period: "AgentReportTimePeriod"
    prompt_text: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        agent_id = str(self.agent_id)

        total_runs = self.total_runs

        success_rate = self.success_rate

        run_statistics = self.run_statistics.to_dict()

        failure_analysis = []
        for failure_analysis_item_data in self.failure_analysis:
            failure_analysis_item = failure_analysis_item_data.to_dict()
            failure_analysis.append(failure_analysis_item)

        failure_categories = self.failure_categories.to_dict()

        supervisor_statistics = self.supervisor_statistics.to_dict()

        time_period = self.time_period.to_dict()

        prompt_text = self.prompt_text

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "agent_id": agent_id,
                "total_runs": total_runs,
                "success_rate": success_rate,
                "run_statistics": run_statistics,
                "failure_analysis": failure_analysis,
                "failure_categories": failure_categories,
                "supervisor_statistics": supervisor_statistics,
                "time_period": time_period,
            }
        )
        if prompt_text is not UNSET:
            field_dict["prompt_text"] = prompt_text

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.agent_report_failure_categories import AgentReportFailureCategories
        from ..models.agent_report_run_statistics import AgentReportRunStatistics
        from ..models.agent_report_supervisor_statistics import AgentReportSupervisorStatistics
        from ..models.agent_report_time_period import AgentReportTimePeriod
        from ..models.failure_report import FailureReport

        d = src_dict.copy()
        agent_id = UUID(d.pop("agent_id"))

        total_runs = d.pop("total_runs")

        success_rate = d.pop("success_rate")

        run_statistics = AgentReportRunStatistics.from_dict(d.pop("run_statistics"))

        failure_analysis = []
        _failure_analysis = d.pop("failure_analysis")
        for failure_analysis_item_data in _failure_analysis:
            failure_analysis_item = FailureReport.from_dict(failure_analysis_item_data)

            failure_analysis.append(failure_analysis_item)

        failure_categories = AgentReportFailureCategories.from_dict(d.pop("failure_categories"))

        supervisor_statistics = AgentReportSupervisorStatistics.from_dict(d.pop("supervisor_statistics"))

        time_period = AgentReportTimePeriod.from_dict(d.pop("time_period"))

        prompt_text = d.pop("prompt_text", UNSET)

        agent_report = cls(
            agent_id=agent_id,
            total_runs=total_runs,
            success_rate=success_rate,
            run_statistics=run_statistics,
            failure_analysis=failure_analysis,
            failure_categories=failure_categories,
            supervisor_statistics=supervisor_statistics,
            time_period=time_period,
            prompt_text=prompt_text,
        )

        agent_report.additional_properties = d
        return agent_report

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
