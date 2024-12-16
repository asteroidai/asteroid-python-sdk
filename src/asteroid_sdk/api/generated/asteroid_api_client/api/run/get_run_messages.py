from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.asteroid_message import AsteroidMessage
from ...models.error_response import ErrorResponse
from ...types import Response


def _get_kwargs(
    run_id: UUID,
    index: int,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/run/{run_id}/messages/{index}",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorResponse, List["AsteroidMessage"]]]:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = AsteroidMessage.from_dict(response_200_item_data)

            response_200.append(response_200_item)

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
) -> Response[Union[ErrorResponse, List["AsteroidMessage"]]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    run_id: UUID,
    index: int,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[ErrorResponse, List["AsteroidMessage"]]]:
    """Get the messages for a run

    Args:
        run_id (UUID):
        index (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, List['AsteroidMessage']]]
    """

    kwargs = _get_kwargs(
        run_id=run_id,
        index=index,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    run_id: UUID,
    index: int,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[ErrorResponse, List["AsteroidMessage"]]]:
    """Get the messages for a run

    Args:
        run_id (UUID):
        index (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, List['AsteroidMessage']]
    """

    return sync_detailed(
        run_id=run_id,
        index=index,
        client=client,
    ).parsed


async def asyncio_detailed(
    run_id: UUID,
    index: int,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Union[ErrorResponse, List["AsteroidMessage"]]]:
    """Get the messages for a run

    Args:
        run_id (UUID):
        index (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, List['AsteroidMessage']]]
    """

    kwargs = _get_kwargs(
        run_id=run_id,
        index=index,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    run_id: UUID,
    index: int,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[Union[ErrorResponse, List["AsteroidMessage"]]]:
    """Get the messages for a run

    Args:
        run_id (UUID):
        index (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, List['AsteroidMessage']]
    """

    return (
        await asyncio_detailed(
            run_id=run_id,
            index=index,
            client=client,
        )
    ).parsed
