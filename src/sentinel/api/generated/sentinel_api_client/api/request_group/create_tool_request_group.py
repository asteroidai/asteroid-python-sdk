from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_response import ErrorResponse
from ...models.tool_request_group import ToolRequestGroup
from ...types import Response


def _get_kwargs(
    tool_id: UUID,
    *,
    body: ToolRequestGroup,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/tool/{tool_id}/request_group",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorResponse, ToolRequestGroup]]:
    if response.status_code == 201:
        response_201 = ToolRequestGroup.from_dict(response.json())

        return response_201
    if response.status_code == 400:
        response_400 = ErrorResponse.from_dict(response.json())

        return response_400
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorResponse, ToolRequestGroup]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    tool_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ToolRequestGroup,
) -> Response[Union[ErrorResponse, ToolRequestGroup]]:
    """Create a new request group for a tool

    Args:
        tool_id (UUID):
        body (ToolRequestGroup):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, ToolRequestGroup]]
    """

    kwargs = _get_kwargs(
        tool_id=tool_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tool_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ToolRequestGroup,
) -> Optional[Union[ErrorResponse, ToolRequestGroup]]:
    """Create a new request group for a tool

    Args:
        tool_id (UUID):
        body (ToolRequestGroup):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, ToolRequestGroup]
    """

    return sync_detailed(
        tool_id=tool_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    tool_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ToolRequestGroup,
) -> Response[Union[ErrorResponse, ToolRequestGroup]]:
    """Create a new request group for a tool

    Args:
        tool_id (UUID):
        body (ToolRequestGroup):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, ToolRequestGroup]]
    """

    kwargs = _get_kwargs(
        tool_id=tool_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tool_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: ToolRequestGroup,
) -> Optional[Union[ErrorResponse, ToolRequestGroup]]:
    """Create a new request group for a tool

    Args:
        tool_id (UUID):
        body (ToolRequestGroup):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, ToolRequestGroup]
    """

    return (
        await asyncio_detailed(
            tool_id=tool_id,
            client=client,
            body=body,
        )
    ).parsed
