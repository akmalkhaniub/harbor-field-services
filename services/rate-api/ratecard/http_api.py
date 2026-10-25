"""HTTP and MCP surface. Azure Functions is a thin host around this module."""

from __future__ import annotations

from dataclasses import dataclass

from ratecard.domain import Caller, InMemoryQuoteStore, QuoteError, QuoteStore, create_quote, get_rate

TOOL_NAMES = ("get_rate", "create_quote")


@dataclass(frozen=True)
class Settings:
    allow_direct: bool = False


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: dict


def _caller(headers: dict[str, str], settings: Settings) -> Caller:
    gateway = headers.get("x-harbor-gateway", "")
    if not settings.allow_direct and gateway != "apim":
        raise QuoteError(401, "unauthenticated", "Calls must come through the Harbor gateway.")
    raw = headers.get("x-harbor-groups", "")
    groups = frozenset(part.strip() for part in raw.split(",") if part.strip())
    return Caller(groups)


def _error(exc: QuoteError) -> HttpResult:
    return HttpResult(exc.status, {"error": exc.code, "message": exc.message})


def _split_path(path: str) -> str:
    cleaned = path.strip("/")
    if cleaned.startswith("api/"):
        cleaned = cleaned[4:]
    return cleaned


def handle(
    method: str,
    path: str,
    query: dict,
    body: dict | None,
    headers: dict[str, str],
    store: QuoteStore,
    settings: Settings,
) -> HttpResult:
    route = _split_path(path)
    normalized = {key.lower(): value for key, value in headers.items()}

    if method == "GET" and route == "health":
        return HttpResult(
            200,
            {
                "status": "ok",
                "service": "harbor-rate-api",
                "store": store.__class__.__name__,
                "allowDirect": settings.allow_direct,
            },
        )

    try:
        caller = _caller(normalized, settings)
        if method == "GET" and route == "rates":
            return HttpResult(200, get_rate(caller, query.get("role"), query.get("accountCode")))
        if method == "POST" and route == "quotes":
            quote = create_quote(caller, body or {}, store)
            return HttpResult(200, quote.as_public())
        if method == "POST" and route == "mcp":
            return _mcp(caller, body or {}, store)
    except QuoteError as exc:
        return _error(exc)

    return HttpResult(404, {"error": "not_found", "message": f"No route for {method} {route}."})


def _mcp(caller: Caller, body: dict, store: QuoteStore) -> HttpResult:
    if body.get("jsonrpc") != "2.0" or "id" not in body:
        raise QuoteError(400, "invalid_jsonrpc", "A JSON-RPC 2.0 request with an id is required.")
    method = body.get("method")
    request_id = body.get("id")

    if method == "initialize":
        return HttpResult(200, {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2025-03-26", "serverInfo": {"name": "harbor-rates", "version": "0.1.0"}, "capabilities": {"tools": {}}}})

    if method == "tools/list":
        tools = [
            {
                "name": "get_rate",
                "description": "Look up the hourly rate for a role on an account the caller can access. Does not approve or send anything.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "accountCode": {"type": "string"},
                    },
                    "required": ["role", "accountCode"],
                },
            },
            {
                "name": "create_quote",
                "description": "Create an idempotent quote. Does not email the client or approve a scope change.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "idempotencyKey": {"type": "string"},
                        "accountCode": {"type": "string"},
                        "role": {"type": "string"},
                        "hours": {"type": "integer"},
                        "afterHours": {"type": "boolean"},
                        "requestedBy": {"type": "string"},
                    },
                    "required": ["idempotencyKey", "accountCode", "role", "hours", "requestedBy"],
                },
            },
        ]
        return HttpResult(200, {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}})

    if method == "tools/call":
        params = body.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in TOOL_NAMES:
            raise QuoteError(404, "unknown_tool", f"Unknown tool '{name}'.")
        if name == "get_rate":
            payload = get_rate(caller, arguments.get("role"), arguments.get("accountCode"))
            text = f"Rate card for {payload['accountCode']} {payload['role']}: USD {payload['hourlyUsd']} per hour before the {payload['discountPercent']}% account discount."
        else:
            quote = create_quote(caller, arguments, store)
            payload = quote.as_public()
            text = (
                f"Quote {quote.quote_id} for USD {quote.amount_usd:.2f} is recorded. "
                "A coordinator still has to approve any scope change at or above the policy threshold. "
                "This tool does not email the client."
            )
        return HttpResult(
            200,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": text}], "structuredContent": payload, "isError": False},
            },
        )

    raise QuoteError(400, "unknown_method", f"Unsupported MCP method '{method}'.")


def default_store() -> InMemoryQuoteStore:
    return InMemoryQuoteStore()
