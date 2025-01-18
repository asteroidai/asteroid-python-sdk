from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.agent_report_supervisor_statistics_reviews_by_type import AgentReportSupervisorStatisticsReviewsByType


T = TypeVar("T", bound="AgentReportSupervisorStatistics")


@_attrs_define
class AgentReportSupervisorStatistics:
    """
    Attributes:
        total_reviews (int):
        reviews_by_type (AgentReportSupervisorStatisticsReviewsByType):
    """

    total_reviews: int
    reviews_by_type: "AgentReportSupervisorStatisticsReviewsByType"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        total_reviews = self.total_reviews

        reviews_by_type = self.reviews_by_type.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "total_reviews": total_reviews,
                "reviews_by_type": reviews_by_type,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.agent_report_supervisor_statistics_reviews_by_type import (
            AgentReportSupervisorStatisticsReviewsByType,
        )

        d = src_dict.copy()
        total_reviews = d.pop("total_reviews")

        reviews_by_type = AgentReportSupervisorStatisticsReviewsByType.from_dict(d.pop("reviews_by_type"))

        agent_report_supervisor_statistics = cls(
            total_reviews=total_reviews,
            reviews_by_type=reviews_by_type,
        )

        agent_report_supervisor_statistics.additional_properties = d
        return agent_report_supervisor_statistics

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
