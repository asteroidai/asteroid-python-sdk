from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.supervision_result import SupervisionResult
from ...types import Response


def _get_kwargs(
    supervision_request_id: UUID,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/supervision_request/{supervision_request_id}/result",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[SupervisionResult]:
    if response.status_code == 200:
        response_200 = SupervisionResult.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[SupervisionResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    supervision_request_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[SupervisionResult]:
    """Get a supervision result

    Args:
        supervision_request_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[SupervisionResult]
    """

    kwargs = _get_kwargs(
        supervision_request_id=supervision_request_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    supervision_request_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[SupervisionResult]:
    """Get a supervision result

    Args:
        supervision_request_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        SupervisionResult
    """

    return sync_detailed(
        supervision_request_id=supervision_request_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    supervision_request_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[SupervisionResult]:
    """Get a supervision result

    Args:
        supervision_request_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[SupervisionResult]
    """

    kwargs = _get_kwargs(
        supervision_request_id=supervision_request_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    supervision_request_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[SupervisionResult]:
    """Get a supervision result

    Args:
        supervision_request_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        SupervisionResult
    """

    return (
        await asyncio_detailed(
            supervision_request_id=supervision_request_id,
            client=client,
        )
    ).parsed
