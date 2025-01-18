from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.supervisor_stats_decisions import SupervisorStatsDecisions


T = TypeVar("T", bound="SupervisorStats")


@_attrs_define
class SupervisorStats:
    """Statistics for a specific type of supervisor

    Attributes:
        total_reviews (int):
        decisions (SupervisorStatsDecisions):
        average_review_time (float): Average time taken for reviews in seconds
        reliability_score (float): Score indicating the reliability of this supervisor type (0-1)
    """

    total_reviews: int
    decisions: "SupervisorStatsDecisions"
    average_review_time: float
    reliability_score: float
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        total_reviews = self.total_reviews

        decisions = self.decisions.to_dict()

        average_review_time = self.average_review_time

        reliability_score = self.reliability_score

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "total_reviews": total_reviews,
                "decisions": decisions,
                "average_review_time": average_review_time,
                "reliability_score": reliability_score,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.supervisor_stats_decisions import SupervisorStatsDecisions

        d = src_dict.copy()
        total_reviews = d.pop("total_reviews")

        decisions = SupervisorStatsDecisions.from_dict(d.pop("decisions"))

        average_review_time = d.pop("average_review_time")

        reliability_score = d.pop("reliability_score")

        supervisor_stats = cls(
            total_reviews=total_reviews,
            decisions=decisions,
            average_review_time=average_review_time,
            reliability_score=reliability_score,
        )

        supervisor_stats.additional_properties = d
        return supervisor_stats

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
