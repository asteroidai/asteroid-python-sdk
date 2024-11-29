from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.tool_request_group import ToolRequestGroup
from ...types import Response


def _get_kwargs(
    request_group_id: UUID,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/request_group/{request_group_id}",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[ToolRequestGroup]:
    if response.status_code == 200:
        response_200 = ToolRequestGroup.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[ToolRequestGroup]:
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
) -> Response[ToolRequestGroup]:
    """Get a request group

    Args:
        request_group_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ToolRequestGroup]
    """

    kwargs = _get_kwargs(
        request_group_id=request_group_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    request_group_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[ToolRequestGroup]:
    """Get a request group

    Args:
        request_group_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ToolRequestGroup
    """

    return sync_detailed(
        request_group_id=request_group_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    request_group_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[ToolRequestGroup]:
    """Get a request group

    Args:
        request_group_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ToolRequestGroup]
    """

    kwargs = _get_kwargs(
        request_group_id=request_group_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    request_group_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[ToolRequestGroup]:
    """Get a request group

    Args:
        request_group_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ToolRequestGroup
    """

    return (
        await asyncio_detailed(
            request_group_id=request_group_id,
            client=client,
        )
    ).parsed
