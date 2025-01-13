from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.asteroid_tool_call import AsteroidToolCall
from ...types import Response


def _get_kwargs(
    tool_call_id: UUID,
    *,
    body: AsteroidToolCall,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "patch",
        "url": f"/tool_call/{tool_call_id}",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[AsteroidToolCall]:
    if response.status_code == 200:
        response_200 = AsteroidToolCall.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[AsteroidToolCall]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    tool_call_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: AsteroidToolCall,
) -> Response[AsteroidToolCall]:
    """Update a tool call

    Args:
        tool_call_id (UUID):
        body (AsteroidToolCall):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AsteroidToolCall]
    """

    kwargs = _get_kwargs(
        tool_call_id=tool_call_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tool_call_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: AsteroidToolCall,
) -> Optional[AsteroidToolCall]:
    """Update a tool call

    Args:
        tool_call_id (UUID):
        body (AsteroidToolCall):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AsteroidToolCall
    """

    return sync_detailed(
        tool_call_id=tool_call_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    tool_call_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: AsteroidToolCall,
) -> Response[AsteroidToolCall]:
    """Update a tool call

    Args:
        tool_call_id (UUID):
        body (AsteroidToolCall):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AsteroidToolCall]
    """

    kwargs = _get_kwargs(
        tool_call_id=tool_call_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tool_call_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: AsteroidToolCall,
) -> Optional[AsteroidToolCall]:
    """Update a tool call

    Args:
        tool_call_id (UUID):
        body (AsteroidToolCall):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AsteroidToolCall
    """

    return (
        await asyncio_detailed(
            tool_call_id=tool_call_id,
            client=client,
            body=body,
        )
    ).parsed
