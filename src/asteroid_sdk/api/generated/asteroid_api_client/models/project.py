import datetime
from typing import Any, Dict, List, Type, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="Project")


@_attrs_define
class Project:
    """
    Attributes:
        id (UUID):
        name (str):
        created_at (datetime.datetime):
        run_result_tags (List[str]):
    """

    id: UUID
    name: str
    created_at: datetime.datetime
    run_result_tags: List[str]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        name = self.name

        created_at = self.created_at.isoformat()

        run_result_tags = self.run_result_tags

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "created_at": created_at,
                "run_result_tags": run_result_tags,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = UUID(d.pop("id"))

        name = d.pop("name")

        created_at = isoparse(d.pop("created_at"))

        run_result_tags = cast(List[str], d.pop("run_result_tags"))

        project = cls(
            id=id,
            name=name,
            created_at=created_at,
            run_result_tags=run_result_tags,
        )

        project.additional_properties = d
        return project

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
