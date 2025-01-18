import datetime
from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="AgentReportTimePeriod")


@_attrs_define
class AgentReportTimePeriod:
    """
    Attributes:
        start_time (datetime.datetime):
        end_time (datetime.datetime):
    """

    start_time: datetime.datetime
    end_time: datetime.datetime
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        start_time = self.start_time.isoformat()

        end_time = self.end_time.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "start_time": start_time,
                "end_time": end_time,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        start_time = isoparse(d.pop("start_time"))

        end_time = isoparse(d.pop("end_time"))

        agent_report_time_period = cls(
            start_time=start_time,
            end_time=end_time,
        )

        agent_report_time_period.additional_properties = d
        return agent_report_time_period

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
