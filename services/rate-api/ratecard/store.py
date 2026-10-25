"""Persistence for quotes. Production uses Azure SQL. Local development uses memory."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Callable

from ratecard.domain import Quote

ConnectionFactory = Callable[[], object]


class SqlQuoteStore:
    """Azure SQL store. The connection factory is injected so tests can fake the cursor."""

    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    def get(self, key: str) -> Quote | None:
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT PayloadJson FROM hf.Quote WHERE IdempotencyKey = ?",
                key,
            )
            row = cursor.fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return Quote(**json.loads(row[0]))

    def put(self, key: str, quote: Quote) -> None:
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO hf.Quote (IdempotencyKey, QuoteId, AccountCode, RoleName, Hours, AmountUsd, PayloadJson)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                key,
                quote.quote_id,
                quote.account_code,
                quote.role,
                quote.hours,
                quote.amount_usd,
                json.dumps(asdict(quote)),
            )
            connection.commit()
        finally:
            connection.close()
