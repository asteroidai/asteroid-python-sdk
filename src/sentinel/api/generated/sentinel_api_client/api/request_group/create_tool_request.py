from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.tool_request import ToolRequest
from ...types import Response


def _get_kwargs(
    request_group_id: UUID,
    *,
    body: ToolRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/request_group/{request_group_id}/tool_requests",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[UUID]:
    if response.status_code == 201:
        response_201 = UUID(response.json())

        return response_201
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[UUID]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    request_group_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ToolRequest,
) -> Response[UUID]:
    """Create a new tool request for a request group

    Args:
        request_group_id (UUID):
        body (ToolRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UUID]
    """

    kwargs = _get_kwargs(
        request_group_id=request_group_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    request_group_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ToolRequest,
) -> Optional[UUID]:
    """Create a new tool request for a request group

    Args:
        request_group_id (UUID):
        body (ToolRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UUID
    """

    return sync_detailed(
        request_group_id=request_group_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    request_group_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ToolRequest,
) -> Response[UUID]:
    """Create a new tool request for a request group

    Args:
        request_group_id (UUID):
        body (ToolRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[UUID]
    """

    kwargs = _get_kwargs(
        request_group_id=request_group_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    request_group_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ToolRequest,
) -> Optional[UUID]:
    """Create a new tool request for a request group

    Args:
        request_group_id (UUID):
        body (ToolRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        UUID
    """

    return (
        await asyncio_detailed(
            request_group_id=request_group_id,
            client=client,
            body=body,
        )
    ).parsed
