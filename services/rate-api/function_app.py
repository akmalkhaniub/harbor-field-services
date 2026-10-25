"""Azure Functions host for the Harbor rate API.

Production runs on the Flex Consumption plan with a managed identity.
Direct calls are rejected unless HARBOR_ALLOW_DIRECT=true, which is for local use.
"""

from __future__ import annotations

import json
import os

import azure.functions as func

from ratecard.http_api import Settings, handle
from ratecard.store import SqlQuoteStore

app = func.FunctionApp()
_store = None


def _build_store():
    connection = os.environ.get("HARBOR_SQL_CONNECTION")
    if connection:
        def connect():
            import pyodbc

            return pyodbc.connect(connection)

        return SqlQuoteStore(connect)
    if os.environ.get("HARBOR_ALLOW_DIRECT", "false").lower() == "true":
        from ratecard.domain import InMemoryQuoteStore

        return InMemoryQuoteStore()
    raise RuntimeError("HARBOR_SQL_CONNECTION is required when HARBOR_ALLOW_DIRECT is false.")


def _store_instance():
    global _store
    if _store is None:
        _store = _build_store()
    return _store


@app.route(route="{*path}", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def harbor(req: func.HttpRequest) -> func.HttpResponse:
    body = None
    if req.method == "POST":
        try:
            body = req.get_json()
        except ValueError:
            body = None
    settings = Settings(allow_direct=os.environ.get("HARBOR_ALLOW_DIRECT", "false").lower() == "true")
    result = handle(
        req.method,
        "/api/" + (req.route_params.get("path") or ""),
        dict(req.params),
        body,
        {key.lower(): value for key, value in req.headers.items()},
        _store_instance(),
        settings,
    )
    return func.HttpResponse(body=json.dumps(result.body), status_code=result.status, mimetype="application/json")
