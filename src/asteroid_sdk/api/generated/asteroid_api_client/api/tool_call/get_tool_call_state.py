from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.run_execution import RunExecution
from ...types import Response


def _get_kwargs(
    tool_call_id: str,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/tool_call/{tool_call_id}/state",
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[RunExecution]:
    if response.status_code == 200:
        response_200 = RunExecution.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[RunExecution]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    tool_call_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[RunExecution]:
    """Get the state of a tool call

    Args:
        tool_call_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[RunExecution]
    """

    kwargs = _get_kwargs(
        tool_call_id=tool_call_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    tool_call_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[RunExecution]:
    """Get the state of a tool call

    Args:
        tool_call_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        RunExecution
    """

    return sync_detailed(
        tool_call_id=tool_call_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    tool_call_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[RunExecution]:
    """Get the state of a tool call

    Args:
        tool_call_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[RunExecution]
    """

    kwargs = _get_kwargs(
        tool_call_id=tool_call_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    tool_call_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[RunExecution]:
    """Get the state of a tool call

    Args:
        tool_call_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        RunExecution
    """

    return (
        await asyncio_detailed(
            tool_call_id=tool_call_id,
            client=client,
        )
    ).parsed
