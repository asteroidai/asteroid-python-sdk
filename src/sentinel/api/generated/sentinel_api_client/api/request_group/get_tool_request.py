from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_response import ErrorResponse
from ...models.tool_request import ToolRequest
from ...types import Response


def _get_kwargs(
    tool_request_id: UUID,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/tool_request/{tool_request_id}",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorResponse, ToolRequest]]:
    if response.status_code == 200:
        response_200 = ToolRequest.from_dict(response.json())

        return response_200
    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())

        return response_404
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorResponse, ToolRequest]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    tool_request_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[ErrorResponse, ToolRequest]]:
    """Get a tool request

    Args:
        tool_request_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, ToolRequest]]
    """

    kwargs = _get_kwargs(
        tool_request_id=tool_request_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tool_request_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[ErrorResponse, ToolRequest]]:
    """Get a tool request

    Args:
        tool_request_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, ToolRequest]
    """

    return sync_detailed(
        tool_request_id=tool_request_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    tool_request_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[ErrorResponse, ToolRequest]]:
    """Get a tool request

    Args:
        tool_request_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, ToolRequest]]
    """

    kwargs = _get_kwargs(
        tool_request_id=tool_request_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tool_request_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[ErrorResponse, ToolRequest]]:
    """Get a tool request

    Args:
        tool_request_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, ToolRequest]
    """

    return (
        await asyncio_detailed(
            tool_request_id=tool_request_id,
            client=client,
        )
    ).parsed
