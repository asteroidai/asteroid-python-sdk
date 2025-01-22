import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.status import Status
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.run_metadata import RunMetadata


T = TypeVar("T", bound="Run")


@_attrs_define
class Run:
    """
    Attributes:
        id (UUID):
        task_id (UUID):
        created_at (datetime.datetime):
        status (Union[Unset, Status]):
        result (Union[Unset, str]):
        metadata (Union[Unset, RunMetadata]):
    """

    id: UUID
    task_id: UUID
    created_at: datetime.datetime
    status: Union[Unset, Status] = UNSET
    result: Union[Unset, str] = UNSET
    metadata: Union[Unset, "RunMetadata"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        task_id = str(self.task_id)

        created_at = self.created_at.isoformat()

        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        result = self.result

        metadata: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.metadata, Unset):
            metadata = self.metadata.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "task_id": task_id,
                "created_at": created_at,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if result is not UNSET:
            field_dict["result"] = result
        if metadata is not UNSET:
            field_dict["metadata"] = metadata

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.run_metadata import RunMetadata

        d = src_dict.copy()
        id = UUID(d.pop("id"))

        task_id = UUID(d.pop("task_id"))

        created_at = isoparse(d.pop("created_at"))

        _status = d.pop("status", UNSET)
        status: Union[Unset, Status]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = Status(_status)

        result = d.pop("result", UNSET)

        _metadata = d.pop("metadata", UNSET)
        metadata: Union[Unset, RunMetadata]
        if isinstance(_metadata, Unset):
            metadata = UNSET
        else:
            metadata = RunMetadata.from_dict(_metadata)

        run = cls(
            id=id,
            task_id=task_id,
            created_at=created_at,
            status=status,
            result=result,
            metadata=metadata,
        )

        run.additional_properties = d
        return run

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
