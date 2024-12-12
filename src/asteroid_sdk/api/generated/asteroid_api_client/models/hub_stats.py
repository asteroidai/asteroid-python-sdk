from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.hub_stats_assigned_reviews import HubStatsAssignedReviews
    from ..models.hub_stats_review_distribution import HubStatsReviewDistribution


T = TypeVar("T", bound="HubStats")


@_attrs_define
class HubStats:
    """
    Attributes:
        connected_clients (int):
        free_clients (int):
        busy_clients (int):
        assigned_reviews (HubStatsAssignedReviews):
        review_distribution (HubStatsReviewDistribution):
        completed_reviews_count (int):
        pending_reviews_count (int):
        assigned_reviews_count (int):
    """

    connected_clients: int
    free_clients: int
    busy_clients: int
    assigned_reviews: "HubStatsAssignedReviews"
    review_distribution: "HubStatsReviewDistribution"
    completed_reviews_count: int
    pending_reviews_count: int
    assigned_reviews_count: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        connected_clients = self.connected_clients

        free_clients = self.free_clients

        busy_clients = self.busy_clients

        assigned_reviews = self.assigned_reviews.to_dict()

        review_distribution = self.review_distribution.to_dict()

        completed_reviews_count = self.completed_reviews_count

        pending_reviews_count = self.pending_reviews_count

        assigned_reviews_count = self.assigned_reviews_count

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "connected_clients": connected_clients,
                "free_clients": free_clients,
                "busy_clients": busy_clients,
                "assigned_reviews": assigned_reviews,
                "review_distribution": review_distribution,
                "completed_reviews_count": completed_reviews_count,
                "pending_reviews_count": pending_reviews_count,
                "assigned_reviews_count": assigned_reviews_count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.hub_stats_assigned_reviews import HubStatsAssignedReviews
        from ..models.hub_stats_review_distribution import HubStatsReviewDistribution

        d = src_dict.copy()
        connected_clients = d.pop("connected_clients")

        free_clients = d.pop("free_clients")

        busy_clients = d.pop("busy_clients")

        assigned_reviews = HubStatsAssignedReviews.from_dict(d.pop("assigned_reviews"))

        review_distribution = HubStatsReviewDistribution.from_dict(d.pop("review_distribution"))

        completed_reviews_count = d.pop("completed_reviews_count")

        pending_reviews_count = d.pop("pending_reviews_count")

        assigned_reviews_count = d.pop("assigned_reviews_count")

        hub_stats = cls(
            connected_clients=connected_clients,
            free_clients=free_clients,
            busy_clients=busy_clients,
            assigned_reviews=assigned_reviews,
            review_distribution=review_distribution,
            completed_reviews_count=completed_reviews_count,
            pending_reviews_count=pending_reviews_count,
            assigned_reviews_count=assigned_reviews_count,
        )

        hub_stats.additional_properties = d
        return hub_stats

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
