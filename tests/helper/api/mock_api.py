import uuid
from http import HTTPStatus
from typing import Any

import httpx


def make_response(json: Any, status_code: HTTPStatus):
    return httpx.Response(
        status_code=status_code,
        headers={},
        json=json
    )

def make_created_response_with_id(resource_id: uuid.UUID):
    return make_response(str(resource_id), HTTPStatus.CREATED)

def make_created_response(json: Any):
    return make_response(json, HTTPStatus.CREATED)

def make_ok_response(json: Any):
    return make_response(json, HTTPStatus.OK)
