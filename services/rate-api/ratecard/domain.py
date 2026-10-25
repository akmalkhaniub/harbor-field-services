"""Quote rules. No HTTP and no Azure types, so the tests can run offline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol
from uuid import uuid4

from ratecard.policy import (
    ACCOUNT_DISCOUNT,
    ACCOUNT_GROUPS,
    AFTER_HOURS_MULTIPLIER,
    FINANCE_GROUP,
    HOURLY_USD,
    MINIMUM_HOURS,
)


class QuoteError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Caller:
    groups: frozenset[str]


@dataclass(frozen=True)
class Quote:
    quote_id: str
    idempotency_key: str
    account_code: str
    role: str
    hours: int
    hourly_usd: int
    discount_percent: float
    after_hours: bool
    amount_usd: float
    requested_by: str
    replayed: bool = False

    def as_public(self) -> dict:
        body = asdict(self)
        body["discount_percent"] = int(self.discount_percent * 100)
        return body


class QuoteStore(Protocol):
    def get(self, key: str) -> Quote | None: ...

    def put(self, key: str, quote: Quote) -> None: ...


class InMemoryQuoteStore:
    def __init__(self) -> None:
        self._quotes: dict[str, Quote] = {}

    def get(self, key: str) -> Quote | None:
        return self._quotes.get(key)

    def put(self, key: str, quote: Quote) -> None:
        self._quotes[key] = quote


def can_access_account(caller: Caller, account_code: str) -> bool:
    if FINANCE_GROUP in caller.groups:
        return True
    required = ACCOUNT_GROUPS.get(account_code)
    return required is not None and required in caller.groups


def quote_amount(role: str, account_code: str, hours: int, after_hours: bool) -> tuple[int, float, float]:
    hourly = HOURLY_USD[role]
    discount = ACCOUNT_DISCOUNT[account_code]
    multiplier = AFTER_HOURS_MULTIPLIER if after_hours else 1.0
    amount = round(hourly * (1 - discount) * multiplier * hours, 2)
    return hourly, discount, amount


def _require_account(account_code: object) -> str:
    if not isinstance(account_code, str) or not account_code.strip():
        raise QuoteError(400, "invalid_account", "Account code is required.")
    code = account_code.strip().upper()
    if code not in ACCOUNT_DISCOUNT:
        raise QuoteError(400, "unknown_account", f"Unknown account '{code}'.")
    return code


def _require_role(role: object) -> str:
    if not isinstance(role, str) or not role.strip():
        raise QuoteError(400, "invalid_role", "Role is required.")
    normalized = role.strip().lower()
    if normalized not in HOURLY_USD:
        raise QuoteError(400, "unknown_role", f"Unknown role '{normalized}'.")
    return normalized


def get_rate(caller: Caller, role: object, account_code: object) -> dict:
    code = _require_account(account_code)
    normalized_role = _require_role(role)
    if not can_access_account(caller, code):
        raise QuoteError(403, "forbidden", "You don't have access to that account.")
    hourly, discount, _ = quote_amount(normalized_role, code, hours=1, after_hours=False)
    return {
        "accountCode": code,
        "role": normalized_role,
        "hourlyUsd": hourly,
        "discountPercent": int(discount * 100),
        "currency": "USD",
    }


def _same_request(existing: Quote, account_code: str, role: str, hours: int, after_hours: bool, requested_by: str) -> bool:
    return (
        existing.account_code == account_code
        and existing.role == role
        and existing.hours == hours
        and existing.after_hours == after_hours
        and existing.requested_by == requested_by
    )


def create_quote(caller: Caller, body: dict, store: QuoteStore) -> Quote:
    if not isinstance(body, dict):
        raise QuoteError(400, "invalid_body", "A JSON object is required.")

    key = body.get("idempotencyKey")
    if not isinstance(key, str) or not 8 <= len(key.strip()) <= 100:
        raise QuoteError(400, "invalid_idempotency_key", "idempotencyKey must be 8 to 100 characters.")
    key = key.strip()

    account_code = _require_account(body.get("accountCode"))
    role = _require_role(body.get("role"))
    hours = body.get("hours")
    if isinstance(hours, bool) or not isinstance(hours, int):
        raise QuoteError(400, "invalid_hours", "Hours must be a whole number.")
    if hours < MINIMUM_HOURS:
        raise QuoteError(400, "below_minimum", f"The minimum engagement is {MINIMUM_HOURS} hours.")

    after_hours = body.get("afterHours", False)
    if not isinstance(after_hours, bool):
        raise QuoteError(400, "invalid_after_hours", "afterHours must be true or false.")

    requested_by = body.get("requestedBy")
    if not isinstance(requested_by, str) or "@" not in requested_by:
        raise QuoteError(400, "invalid_requested_by", "requestedBy must be an email address.")

    if not can_access_account(caller, account_code):
        raise QuoteError(403, "forbidden", "You don't have access to that account.")

    existing = store.get(key)
    if existing is not None:
        if not _same_request(existing, account_code, role, hours, after_hours, requested_by):
            raise QuoteError(409, "idempotency_conflict", "This idempotency key was already used for a different quote.")
        return Quote(
            quote_id=existing.quote_id,
            idempotency_key=existing.idempotency_key,
            account_code=existing.account_code,
            role=existing.role,
            hours=existing.hours,
            hourly_usd=existing.hourly_usd,
            discount_percent=existing.discount_percent,
            after_hours=existing.after_hours,
            amount_usd=existing.amount_usd,
            requested_by=existing.requested_by,
            replayed=True,
        )

    hourly, discount, amount = quote_amount(role, account_code, hours, after_hours)
    created = Quote(
        quote_id=str(uuid4()),
        idempotency_key=key,
        account_code=account_code,
        role=role,
        hours=hours,
        hourly_usd=hourly,
        discount_percent=discount,
        after_hours=after_hours,
        amount_usd=amount,
        requested_by=requested_by,
        replayed=False,
    )
    store.put(key, created)
    return created
