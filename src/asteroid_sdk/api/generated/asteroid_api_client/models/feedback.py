import datetime
from typing import Any, Dict, List, Type, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="Feedback")


@_attrs_define
class Feedback:
    """
    Attributes:
        id (UUID):
        run_id (UUID):
        created_at (datetime.datetime): The timestamp of when the feedback was created
        updated_at (datetime.datetime): The timestamp of when the feedback was last updated
        feedback (str):
    """

    id: UUID
    run_id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    feedback: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        run_id = str(self.run_id)

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        feedback = self.feedback

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "run_id": run_id,
                "created_at": created_at,
                "updated_at": updated_at,
                "feedback": feedback,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = UUID(d.pop("id"))

        run_id = UUID(d.pop("run_id"))

        created_at = isoparse(d.pop("created_at"))

        updated_at = isoparse(d.pop("updated_at"))

        feedback = d.pop("feedback")

        feedback = cls(
            id=id,
            run_id=run_id,
            created_at=created_at,
            updated_at=updated_at,
            feedback=feedback,
        )

        feedback.additional_properties = d
        return feedback

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
