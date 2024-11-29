from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_response import ErrorResponse
from ...models.supervision_request import SupervisionRequest
from ...types import Response


def _get_kwargs(
    request_group_id: UUID,
    chain_id: UUID,
    supervisor_id: UUID,
    *,
    body: SupervisionRequest,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/request_group/{request_group_id}/chain/{chain_id}/supervisor/{supervisor_id}/supervision_request",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorResponse, UUID]]:
    if response.status_code == 201:
        response_201 = UUID(response.json())

        return response_201
    if response.status_code == 400:
        response_400 = ErrorResponse.from_dict(response.json())

        return response_400
    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())

        return response_404
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorResponse, UUID]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    request_group_id: UUID,
    chain_id: UUID,
    supervisor_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: SupervisionRequest,
) -> Response[Union[ErrorResponse, UUID]]:
    """Create a supervision request for a supervisor in a chain on a request group

    Args:
        request_group_id (UUID):
        chain_id (UUID):
        supervisor_id (UUID):
        body (SupervisionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, UUID]]
    """

    kwargs = _get_kwargs(
        request_group_id=request_group_id,
        chain_id=chain_id,
        supervisor_id=supervisor_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    request_group_id: UUID,
    chain_id: UUID,
    supervisor_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: SupervisionRequest,
) -> Optional[Union[ErrorResponse, UUID]]:
    """Create a supervision request for a supervisor in a chain on a request group

    Args:
        request_group_id (UUID):
        chain_id (UUID):
        supervisor_id (UUID):
        body (SupervisionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, UUID]
    """

    return sync_detailed(
        request_group_id=request_group_id,
        chain_id=chain_id,
        supervisor_id=supervisor_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    request_group_id: UUID,
    chain_id: UUID,
    supervisor_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: SupervisionRequest,
) -> Response[Union[ErrorResponse, UUID]]:
    """Create a supervision request for a supervisor in a chain on a request group

    Args:
        request_group_id (UUID):
        chain_id (UUID):
        supervisor_id (UUID):
        body (SupervisionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorResponse, UUID]]
    """

    kwargs = _get_kwargs(
        request_group_id=request_group_id,
        chain_id=chain_id,
        supervisor_id=supervisor_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    request_group_id: UUID,
    chain_id: UUID,
    supervisor_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
    body: SupervisionRequest,
) -> Optional[Union[ErrorResponse, UUID]]:
    """Create a supervision request for a supervisor in a chain on a request group

    Args:
        request_group_id (UUID):
        chain_id (UUID):
        supervisor_id (UUID):
        body (SupervisionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorResponse, UUID]
    """

    return (
        await asyncio_detailed(
            request_group_id=request_group_id,
            chain_id=chain_id,
            supervisor_id=supervisor_id,
            client=client,
            body=body,
        )
    ).parsed
