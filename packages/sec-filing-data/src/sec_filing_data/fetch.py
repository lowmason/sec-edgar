"""The `fetch` command: fetch each sampled submission file once, in draw order.

This module and `client.py` are the only ones that send SEC requests.
"""

import time
from collections import Counter
from collections.abc import Callable
from operator import itemgetter

from sec_filing_data.client import AccessDenied, BudgetExhausted, SecClient, exclusive_lock
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import build_fetches
from sec_filing_data.tables import read_table, write_table

BUDGET_SPENT_EXIT = 5
ACCESS_DENIED_EXIT = 6


def run_fetch(
    layout: Layout,
    *,
    user_agent: str,
    per_form: int | None = None,
    session=None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Fetch each sampled filing that is not on disk yet, and write the `fetches` table.

    With `per_form`, only the first `per_form` quota rows of each form are walked. Returns
    0 after a full walk, 5 when the budget is spent and 6 when SEC answers 403. Every exit,
    an exception included, writes `fetches`. A held lock raises RuntimeError and writes
    nothing. `monotonic` and `sleep` go to the client, so tests need not wait.
    """
    with exclusive_lock(layout.lock):
        rows = _rows_to_walk(read_table(layout, "sample").to_pylist(), per_form)
        sec = SecClient(
            user_agent, layout.ledger, session=session, monotonic=monotonic, sleep=sleep
        )
        try:
            return _walk(layout, sec, rows)
        finally:
            write_table(layout, "fetches", build_fetches(layout))


def _rows_to_walk(sample: list[dict], per_form: int | None) -> list[dict]:
    rows = sorted(sample, key=itemgetter("draw"))
    if per_form is None:
        return rows
    taken: Counter[str] = Counter()
    chosen = []
    for row in rows:
        if row["stratum"] == "quota" and taken[row["form_type"]] < per_form:
            taken[row["form_type"]] += 1
            chosen.append(row)
    return chosen


def _walk(layout: Layout, sec: SecClient, rows: list[dict]) -> int:
    for row in rows:
        accession = row["accession_number"]
        dest = layout.submission(accession)
        if dest.exists():
            continue
        # A hard kill can leave a partial file behind. The fetch starts it again.
        dest.with_name(dest.name + ".part").unlink(missing_ok=True)
        try:
            sec.fetch(row["url"], dest, key=accession)
        except BudgetExhausted:
            return BUDGET_SPENT_EXIT
        except AccessDenied:
            return ACCESS_DENIED_EXIT
    return 0
