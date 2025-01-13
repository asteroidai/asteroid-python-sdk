from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import Response


def _get_kwargs(
    run_id: UUID,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
<<<<<<<< HEAD:src/asteroid_sdk/api/generated/asteroid_api_client/api/api_key/validate_api_key.py
        "method": "get",
        "url": "/api_key/validate",
========
        "method": "delete",
        "url": f"/run/{run_id}",
>>>>>>>> 2bb95f8 (Add API key management endpoints and models):src/asteroid_sdk/api/generated/asteroid_api_client/api/run/delete_run.py
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Any]:
    if response.status_code == 200:
        return None
    if response.status_code == 401:
        return None
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Any]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    run_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Any]:
<<<<<<<< HEAD:src/asteroid_sdk/api/generated/asteroid_api_client/api/api_key/validate_api_key.py
    """Validate an API key
========
    """Delete a run

    Args:
        run_id (UUID):
>>>>>>>> 2bb95f8 (Add API key management endpoints and models):src/asteroid_sdk/api/generated/asteroid_api_client/api/run/delete_run.py

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        run_id=run_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    run_id: UUID,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Any]:
<<<<<<<< HEAD:src/asteroid_sdk/api/generated/asteroid_api_client/api/api_key/validate_api_key.py
    """Validate an API key
========
    """Delete a run

    Args:
        run_id (UUID):
>>>>>>>> 2bb95f8 (Add API key management endpoints and models):src/asteroid_sdk/api/generated/asteroid_api_client/api/run/delete_run.py

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        run_id=run_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)
