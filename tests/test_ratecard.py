from ratecard.domain import Caller, InMemoryQuoteStore, QuoteError, create_quote, get_rate
from ratecard.http_api import Settings, handle
from ratecard.store import SqlQuoteStore


def _caller(*groups: str) -> Caller:
    return Caller(frozenset(groups))


def _quote(**overrides):
    body = {
        "idempotencyKey": "quote-1001",
        "accountCode": "NORTH",
        "role": "senior",
        "hours": 6,
        "afterHours": False,
        "requestedBy": "ada@harbor.example",
    }
    body.update(overrides)
    return body


def test_standard_quote_uses_the_rate_card():
    quote = create_quote(_caller("hf-acct-north"), _quote(), InMemoryQuoteStore())
    assert quote.amount_usd == 1440
    assert quote.replayed is False


def test_account_discount_and_after_hours_stack():
    quote = create_quote(
        _caller("hf-finance"),
        _quote(accountCode="BRIGHT", role="principal", hours=4, afterHours=True, idempotencyKey="quote-1002"),
        InMemoryQuoteStore(),
    )
    assert quote.hourly_usd == 320
    assert quote.discount_percent == 0.10
    assert quote.amount_usd == 1440


def test_minimum_hours_and_unknown_role_are_rejected():
    store = InMemoryQuoteStore()
    try:
        create_quote(_caller("hf-acct-north"), _quote(hours=2), store)
        raise AssertionError("expected minimum hours to fail")
    except QuoteError as exc:
        assert exc.status == 400
        assert exc.code == "below_minimum"
    try:
        create_quote(_caller("hf-acct-north"), _quote(role="intern"), store)
        raise AssertionError("expected unknown role to fail")
    except QuoteError as exc:
        assert exc.code == "unknown_role"


def test_cross_account_quote_is_forbidden():
    try:
        create_quote(_caller("hf-acct-north"), _quote(accountCode="bright"), InMemoryQuoteStore())
        raise AssertionError("expected forbidden")
    except QuoteError as exc:
        assert exc.status == 403


def test_repeated_key_replays_and_a_changed_payload_conflicts():
    store = InMemoryQuoteStore()
    caller = _caller("hf-acct-north")
    first = create_quote(caller, _quote(), store)
    second = create_quote(caller, _quote(), store)
    assert second.quote_id == first.quote_id
    assert second.replayed is True
    try:
        create_quote(caller, _quote(hours=8), store)
        raise AssertionError("expected conflict")
    except QuoteError as exc:
        assert exc.status == 409


def test_direct_calls_are_rejected_unless_the_gateway_header_is_present():
    store = InMemoryQuoteStore()
    blocked = handle("GET", "/api/rates", {"role": "senior", "accountCode": "NORTH"}, None, {"x-harbor-groups": "hf-acct-north"}, store, Settings(allow_direct=False))
    assert blocked.status == 401
    allowed = handle(
        "GET",
        "/api/rates",
        {"role": "senior", "accountCode": "NORTH"},
        None,
        {"x-harbor-gateway": "apim", "x-harbor-groups": "hf-acct-north"},
        store,
        Settings(allow_direct=False),
    )
    assert allowed.status == 200
    assert allowed.body["hourlyUsd"] == 240


def test_mcp_exposes_read_and_quote_tools_only():
    result = handle(
        "POST",
        "/api/mcp",
        {},
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {"x-harbor-groups": "hf-finance"},
        InMemoryQuoteStore(),
        Settings(allow_direct=True),
    )
    names = [tool["name"] for tool in result.body["result"]["tools"]]
    assert names == ["get_rate", "create_quote"]
    assert "send_email" not in names
    assert "approve" not in names


def test_mcp_quote_does_not_claim_the_client_was_emailed():
    result = handle(
        "POST",
        "/api/mcp",
        {},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "create_quote", "arguments": _quote(idempotencyKey="quote-mcp-1")},
        },
        {"x-harbor-groups": "hf-acct-north"},
        InMemoryQuoteStore(),
        Settings(allow_direct=True),
    )
    text = result.body["result"]["content"][0]["text"]
    assert "does not email the client" in text
    assert result.body["result"]["isError"] is False


def test_sql_store_round_trips_the_idempotency_row():
    saved = {}

    class Cursor:
        def execute(self, sql, *args):
            self.sql = sql
            self.args = args
            if sql.strip().upper().startswith("SELECT"):
                self._row = saved.get(args[0])
            else:
                saved[args[0]] = args[-1]
                self._row = None

        def fetchone(self):
            if self._row is None:
                return None
            return (self._row,)

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            return None

        def close(self):
            return None

    store = SqlQuoteStore(lambda: Connection())
    quote = create_quote(_caller("hf-finance"), _quote(idempotencyKey="quote-sql-1"), store)
    assert store.get("quote-sql-1").quote_id == quote.quote_id


def test_get_rate_hides_other_accounts():
    try:
        get_rate(_caller("hf-acct-bright"), "senior", "NORTH")
        raise AssertionError("expected forbidden")
    except QuoteError as exc:
        assert exc.status == 403
