"""Distributed issuance invariants against durable offline lease/journal stores."""
import importlib
import importlib.util
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from support import FixtureClock, fixture_context, fixture_settings, store_bundle
from sec_edgar_ingest.models import Permit
from sec_edgar_ingest.storage.contracts import Conflict, OwnershipLost


class JournalContractTests(unittest.TestCase):
    def test_journal_is_durable_and_fenced_by_actual_lease_and_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root, clock = Path(directory), FixtureClock()
            _, _, leases = store_bundle(root, clock=clock)
            self.addCleanup(leases.close)
            handle = leases.acquire("old", 60)
            self.assertTrue(hasattr(leases, "read_journal"), "The leased sentinel must expose a durable fenced journal")
            row = leases.read_journal(handle)
            value = {"epoch": 1, "last_start": clock.now().isoformat(), "nested": {"x": [1]}}
            written = leases.write_journal(handle, value, row.version)
            value["nested"]["x"].append(2)
            self.assertEqual(written.value["nested"]["x"], (1,))
            with self.assertRaises(Conflict):
                leases.write_journal(handle, {"epoch": 9}, row.version)
            leases.close()
            _, _, reopened = store_bundle(root, clock=clock)
            self.addCleanup(reopened.close)
            self.assertEqual(reopened.read_journal(handle).value["epoch"], 1)
            clock.advance(60)
            successor = reopened.acquire("new", 60)
            for operation in (lambda: reopened.read_journal(handle),
                              lambda: reopened.write_journal(handle, {"epoch": 9}, written.version)):
                with self.assertRaises(OwnershipLost):
                    operation()
            self.assertEqual(reopened.read_journal(successor).value["epoch"], 1)

    def test_permit_exposes_detached_validated_persisted_next_allowed_time(self):
        clock = FixtureClock()
        permit = Permit("owner", 1, "request", clock.now()+timedelta(seconds=1),
                        clock.now()+timedelta(seconds=90), clock.now()+timedelta(seconds=152), 1, 90)
        self.assertIn("next_allowed_at", permit.to_mapping(), "The transport row needs the journal's durable next-start/cooldown")
        future = clock.now()+timedelta(seconds=12)
        permit = replace(permit, next_allowed_at=future)
        mapping = permit.to_mapping()
        mapping["next_allowed_at"] = None
        self.assertEqual(permit.next_allowed_at, future)
        self.assertEqual(Permit.from_mapping(permit.to_mapping()), permit)
        for invalid in ("later", future.replace(tzinfo=None), True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                replace(permit, next_allowed_at=invalid)

    def azure_leases(self, responses, clock=None):
        from azure.storage.blob import BlobServiceClient
        from sec_edgar_ingest.storage.azure import AzureLeaseStore
        from test_azure_contracts import BLOB_ENDPOINT, RETRY, ScriptedTransport
        transport = ScriptedTransport(responses)
        service = BlobServiceClient(BLOB_ENDPOINT, api_version="2026-04-06", transport=transport, **RETRY)
        self.addCleanup(service.close)
        return AzureLeaseStore(service, clock=clock or FixtureClock()), transport

    def test_upper_bounds_include_server_date_precision_and_rtt(self):
        from test_azure_contracts import response
        clock = FixtureClock()
        leases, transport = self.azure_leases([response(201), response(201, headers={"x-ms-lease-id": "real"})], clock)
        send = transport.send
        def measured_send(request, **kwargs):
            if request.headers.get("x-ms-lease-action") == "acquire":
                clock.advance(0.5)
            return send(request, **kwargs)
        transport.send = measured_send
        handle = leases.acquire("one", 60)
        self.assertEqual(handle.observed_until, FixtureClock().now()+timedelta(seconds=58))
        self.assertEqual(getattr(handle, "acquired_upper", None), FixtureClock().now()+timedelta(seconds=1.5),
                         "Expiry/takeover need the server upper bound, never the lower observed_until")
        self.assertEqual(handle.ownership_until_upper, FixtureClock().now()+timedelta(seconds=61.5))

    def test_date_precision_plus_rtt_must_fit_two_second_bound(self):
        from sec_edgar_ingest.storage.contracts import ClockUncertain
        from test_azure_contracts import response
        clock = FixtureClock()
        leases, transport = self.azure_leases([response(201), response(201, headers={"x-ms-lease-id": "real"})], clock)
        send = transport.send
        def measured_send(request, **kwargs):
            if request.headers.get("x-ms-lease-action") == "acquire":
                clock.advance(1.01)
            return send(request, **kwargs)
        transport.send = measured_send
        with self.assertRaises(ClockUncertain):
            leases.acquire("one", 60)

    def test_azure_journal_fences_read_and_write_with_lease_and_actual_etag(self):
        from sec_edgar_ingest.storage.contracts import LeaseHandle
        from test_azure_contracts import response
        clock = FixtureClock()
        leases, transport = self.azure_leases([response(etag='"first"'), response(etag='"first"', body=b'{"epoch":4}'),
                                               response(201, etag='"read-fenced"'), response(201, etag='"written"')], clock)
        handle = LeaseHandle("one", "real", clock.now()+timedelta(seconds=58))
        self.assertTrue(hasattr(leases, "read_journal"), "Azure sentinel journal must use actual leased Blob operations")
        read = leases.read_journal(handle)
        self.assertEqual(read.version, '"read-fenced"')
        written = leases.write_journal(handle, {"epoch": 5}, read.version)
        self.assertEqual(written.version, '"written"')
        for request in transport.requests:
            self.assertEqual(request.headers["x-ms-lease-id"], "real")
        self.assertEqual(transport.requests[1].headers["If-Match"], '"first"')
        self.assertEqual(transport.requests[2].headers["If-Match"], '"first"')
        self.assertEqual(transport.requests[3].headers["If-Match"], '"read-fenced"')
        self.assertFalse(transport.responses)

    def test_actual_azure_release_never_writes_a_shortened_guard(self):
        from azure.core.exceptions import HttpResponseError
        from sec_edgar_ingest.storage.contracts import LeaseHandle
        from test_azure_contracts import response, blob_error
        for unknown in (False, True):
            with self.subTest(unknown=unknown):
                clock = FixtureClock()
                body = b'{"clean_release":false,"unsafe_until":"2026-10-06T00:02:32+00:00"}'
                final = blob_error(500, "InternalError") if unknown else response()
                leases, transport = self.azure_leases([response(etag='"old"'), response(etag='"old"', body=body),
                                                       response(201, etag='"fenced"'), final], clock)
                handle = LeaseHandle("one", "actual-id", clock.now()+timedelta(seconds=58))
                row = leases.read_journal(handle)
                if unknown:
                    with self.assertRaises(HttpResponseError):
                        leases.release(handle)
                else:
                    leases.release(handle)
                writes = [request for request in transport.requests if request.method == "PUT" and "comp=lease" not in request.url]
                self.assertEqual([request.body for request in writes], [body])
                self.assertEqual(row.value["unsafe_until"], "2026-10-06T00:02:32+00:00")
                self.assertFalse(row.value["clean_release"])
                self.assertFalse(callable(getattr(leases, "release_clean", None)))
                self.assertEqual(transport.requests[-1].headers["x-ms-lease-action"], "release")
                self.assertEqual(transport.requests[-1].headers["x-ms-lease-id"], "actual-id")
                self.assertFalse(transport.responses)

    def test_azure_journal_id_etag_and_outage_fail_closed(self):
        from sec_edgar_ingest.storage.contracts import LeaseHandle
        from azure.core.exceptions import HttpResponseError
        from test_azure_contracts import blob_error
        for code, status in (("LeaseIdMismatchWithBlobOperation", 412), ("ConditionNotMet", 412), ("InternalError", 500)):
            for method in ("read", "write"):
                with self.subTest(code=code, method=method):
                    clock = FixtureClock()
                    leases, transport = self.azure_leases([blob_error(status, code)], clock)
                    handle = LeaseHandle("one", "stale", clock.now()+timedelta(seconds=58))
                    operation = (lambda: leases.read_journal(handle)) if method == "read" else (lambda: leases.write_journal(handle, {}, '"old"'))
                    with self.assertRaises(HttpResponseError if status == 500 else OwnershipLost):
                        operation()
                    self.assertEqual(len(transport.requests), 1)

    def test_local_acquisition_upper_is_observed_after_conditional_confirmation(self):
        from support import Faults
        with tempfile.TemporaryDirectory() as directory:
            clock, faults = FixtureClock(), Faults()
            _, _, leases = store_bundle(Path(directory), clock=clock, observer=faults)
            self.addCleanup(leases.close)
            faults.at("state.after_insert", lambda: clock.advance(0.25))
            handle = leases.acquire("one", 60)
            self.assertGreaterEqual(handle.acquired_upper, clock.now(),
                                    "The upper acquisition observation must follow the actual conditional create confirmation")
            self.assertEqual(handle.acquired_upper, handle.observation.upper)

    def test_local_server_observation_bounds_paired_sampling_latency(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = FixtureClock()
            _, _, leases = store_bundle(Path(directory), clock=clock)
            self.addCleanup(leases.close)
            original_now = clock.now
            def measured_now():
                instant = original_now()
                clock.advance(0.1)
                return instant
            clock.now = measured_now
            bounds = leases.observe_time()
            self.assertEqual(bounds.lower, FixtureClock().now())
            self.assertGreaterEqual(bounds.upper, clock.instant,
                                    "Pairing old UTC with a later monotonic sample needs the full measured sampling interval")
            self.assertEqual(bounds.monotonic_at, clock.monotonic())


    def test_local_constructor_recovers_real_wal_transition_contention_and_skips_warm_transition(self):
        import sqlite3
        from unittest.mock import patch
        from sec_edgar_ingest.storage.local import LocalStateStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = LocalStateStore(root)
            initial.close()
            connect = sqlite3.connect
            blocker = connect(root / "state.sqlite3", timeout=0)
            self.addCleanup(blocker.close)
            blocker.execute("PRAGMA journal_mode=DELETE")
            blocker.execute("BEGIN")
            blocker.execute("SELECT * FROM records").fetchall()
            busy, statements = [], []
            release_after_busy = True
            class ObservedConnection:
                def __init__(self, actual):
                    self.actual = actual
                def __getattr__(self, name):
                    return getattr(self.actual, name)
                def execute(self, sql, *args):
                    statements.append(sql)
                    try:
                        return self.actual.execute(sql, *args)
                    except sqlite3.OperationalError as error:
                        if sql == "PRAGMA journal_mode=WAL":
                            busy.append(error.sqlite_errorcode)
                            # The losing mode-transition attempt sees real SQLITE_BUSY before its peer drains.
                            if release_after_busy:
                                blocker.rollback()
                        raise
            def observed_connect(*args, **kwargs):
                kwargs["timeout"] = 0
                return ObservedConnection(connect(*args, **kwargs))
            with patch("sec_edgar_ingest.storage.local.sqlite3.connect", observed_connect):
                recovered = LocalStateStore(root)
                self.addCleanup(recovered.close)
                self.assertEqual(busy, [sqlite3.SQLITE_BUSY])
                statements.clear()
                warm = LocalStateStore(root)
                self.addCleanup(warm.close)
                self.assertNotIn("PRAGMA journal_mode=WAL", statements,
                                 "An initialized durable root must not attempt another WAL mode transition")
                warm.insert("QueueTicket", "constructor-probe", {"ok": True})
                self.assertTrue(recovered.get("QueueTicket", "constructor-probe").value["ok"])
                # Reopen after the peer's mode change; the old connection caches its DELETE mode.
                blocker.close()
                blocker = connect(root / "state.sqlite3", timeout=0)
                self.addCleanup(blocker.close)
                self.assertEqual(blocker.execute("PRAGMA journal_mode=DELETE").fetchone()[0], "delete")
                blocker.execute("BEGIN")
                blocker.execute("SELECT * FROM records").fetchall()
                release_after_busy = False
                busy.clear()
                try:
                    with self.assertRaises(sqlite3.OperationalError):
                        LocalStateStore(root)
                    self.assertEqual(busy, [sqlite3.SQLITE_BUSY]*3,
                                     "A persistent startup lock must fail closed after finite attempts")
                finally:
                    blocker.rollback()

    def test_three_simultaneous_constructors_on_initialized_root_share_actual_state(self):
        from sec_edgar_ingest.storage.local import LocalStateStore
        from support import constructor_process_probe
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = LocalStateStore(root)
            initial.close()
            trace = constructor_process_probe(root)
            completed = [event for event in trace if event["event"] == "constructed"]
            self.assertEqual(len(completed), 3)
            self.assertEqual(len({event["pid"] for event in completed}), 3)
            reopened = LocalStateStore(root)
            self.addCleanup(reopened.close)
            self.assertEqual(len(tuple(reopened.scan("QueueTicket", {}))), 3)


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("sec_edgar_ingest.coordination"),
                             "Every SEC request needs finite leased-journal coordination")
        self.coordination = importlib.import_module("sec_edgar_ingest.coordination")
        self.harness_count = 0
        self.events = []

    def tearDown(self):
        from support import retain_coordination_trace
        if self.events:
            retain_coordination_trace(self._testMethodName+".json", self.events)

    def harness(self, root, clock):
        from support import coordination_harness
        h = coordination_harness(root, clock=clock)
        self.harness_count += 1
        h.trace_name = self._testMethodName+f"-{self.harness_count}.json"
        return h

    def test_expired_lease_does_not_allow_overlap_with_old_request(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("backfill-a", "backfill")
        clock.advance(59)
        h.hold_request("backfill-a")
        old_end = h.permits["backfill-a"].must_end_by
        h.expire_owner("backfill-a")
        h.acquire_successor("daily-b")
        guard = h.turns["daily-b"].earliest_safe
        self.assertGreaterEqual(guard, old_end)
        self.assertGreaterEqual(guard, clock.now()+timedelta(seconds=92))
        clock.advance((old_end-clock.now()).total_seconds()-1)
        self.assertEqual([owner for owner, _ in h.starts], ["backfill-a"])
        h.finish_request("backfill-a")
        clock.advance(2)
        h.reserve("daily-b")
        self.assertEqual(h.maximum_active, 1)
        self.assertEqual([owner for owner, _ in h.starts], ["backfill-a", "daily-b"])

    def test_delayed_dispatch_cannot_compress_actual_socket_starts(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("one", "backfill")
        permit = h.turns["one"].reserve("delayed")
        clock.advance(permit.start_before_mono-clock.monotonic()-0.00001)
        h.dispatch("one", permit)
        h.finish_request("one")
        h.start("two", "daily")
        h.reserve("two")
        self.assertGreaterEqual((h.starts[1][1]-h.starts[0][1]).total_seconds(), 1/3)

    def test_stale_epoch_and_dispatch_deadline_are_refused(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("one", "backfill")
        permit = h.turns["one"].reserve("stale")
        clock.advance(permit.start_before_mono-clock.monotonic()+0.00001)
        with self.assertRaises(OwnershipLost):
            h.turns["one"].assert_current(permit)
        self.assertTrue(h.turns["one"].cancelled.is_set())
        self.assertEqual(h.starts, [])

    def test_restart_retains_global_cooldown(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock = Path(directory), fixture_clock()
        h = self.harness(root, clock)
        h.start("one", "backfill")
        h.reserve("one")
        until = clock.now()+timedelta(seconds=120)
        h.coordinators["one"].defer_until(until)
        h.finish_request("one")
        h.close()
        reopened = self.harness(root, clock)
        self.addCleanup(reopened.close)
        reopened.start("daily", "daily")
        reopened.reserve("daily")
        self.assertGreaterEqual(reopened.starts[0][1], until)


    def build(self, root, clock, faults=None):
        state, _, leases = store_bundle(root, clock=clock, observer=faults)
        self.addCleanup(state.close)
        self.addCleanup(leases.close)
        coordinator = self.coordination.Coordinator(fixture_settings(), state, leases, clock)
        coordinator.observer = self.events.append
        return coordinator, leases

    def test_takeover_guard_remains_fixed_while_successor_renews(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("old", "backfill")
        h.hold_request("old")
        h.expire_owner("old")
        h.acquire_successor("new")
        earliest = h.turns["new"].earliest_safe
        for ordinal in range(4):
            clock.advance(20)
            self.assertEqual(h.turns["new"].earliest_safe, earliest)
            if ordinal == 0:
                h.finish_request("old")
        self.assertGreater(h.turns["new"].handle.ownership_until_upper, earliest)
        h.reserve("new")
        self.assertGreaterEqual(h.starts[-1][1], earliest)
        self.assertEqual(h.maximum_active, 1)

    def test_unknown_renewal_outcome_waits_full_exchange_after_confirmed_acquisition(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("old", "backfill")
        h.hold_request("old")
        def unknown():
            raise TimeoutError("renewal committed but acknowledgement lost")
        h.faults["old"].at("lease.after_renew", unknown)
        clock.advance(20)
        self.assertTrue(h.turns["old"].cancelled.is_set())
        clock.advance(60)
        h.acquire_successor("new")
        acquired = h.turns["new"].handle.acquired_upper
        self.assertGreaterEqual(h.turns["new"].earliest_safe, acquired+timedelta(seconds=92))
        clock.advance(10)
        h.finish_request("old")
        h.reserve("new")
        self.assertGreaterEqual(h.starts[-1][1], acquired+timedelta(seconds=92))
        self.assertEqual(h.maximum_active, 1)

    def test_renewal_loss_during_body_returns_retained_partial_and_shared_cancellation(self):
        from support import ControlledSender, Faults, fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock, faults = Path(directory), fixture_clock(), Faults()
        coordinator, leases = self.build(root, clock, faults)
        events = self.events
        coordinator.observer = events.append
        def renewal_fails():
            raise TimeoutError("unknown renewal outcome")
        faults.at("lease.after_renew", renewal_fails)
        sender = ControlledSender(root, clock, on_send=lambda cancellation, permit: clock.advance(20))
        receipt = coordinator.exchange(fixture_context(), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
        self.assertFalse(receipt.complete)
        self.assertEqual(receipt.error.code, "ownership_lost")
        self.assertTrue(receipt.temporary_path.exists())
        self.assertGreater(receipt.byte_count, 0)
        self.assertTrue(sender.cancellations[0].is_set())
        self.assertTrue(any(event["event"] == "loss" for event in events))
        self.assertEqual(len(sender.starts), 1)

    def test_reservation_outage_stops_dispatch_and_keeps_durable_guard(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("old", "backfill")
        def unknown():
            raise OSError("journal committed but reply lost")
        h.faults["old"].at("journal.after_write", unknown)
        with self.assertRaises(OwnershipLost):
            h.turns["old"].reserve("uncertain-unused-slot")
        self.assertTrue(h.turns["old"].cancelled.is_set())
        row = h.leases["old"].read_journal(h.turns["old"].handle)
        self.assertFalse(row.value["clean_release"])
        self.assertIsNotNone(row.value["last_start"])
        self.assertEqual(h.starts, [])
        h.expire_owner("old")
        h.acquire_successor("new")
        self.assertGreaterEqual(h.turns["new"].earliest_safe, self.coordination.utc_value(row.value["unsafe_until"]))
        h.reserve("new")
        self.assertEqual([owner for owner, _ in h.starts], ["new"])

    def test_clock_uncertainty_stops_before_sender(self):
        from support import fixture_clock
        from sec_edgar_ingest.storage.contracts import TimeBounds
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("old", "backfill")
        observe_time = h.leases["old"].observe_time
        h.leases["old"].observe_time = lambda handle=None: TimeBounds(clock.now(), clock.now()+timedelta(seconds=2.01), clock.monotonic())
        with self.assertRaises(OwnershipLost):
            h.reserve("old")
        self.assertTrue(h.turns["old"].cancelled.is_set())
        self.assertEqual(h.starts, [])
        h.leases["old"].observe_time = observe_time
        row = h.leases["old"].read_journal(h.turns["old"].handle)
        self.assertFalse(row.value["clean_release"])

    def test_expired_queue_ticket_is_cas_retired_without_erasing_another(self):
        from support import ControlledSender, fixture_clock
        from sec_edgar_ingest.models import QueueTicket
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock = Path(directory), fixture_clock()
        coordinator, _ = self.build(root, clock)
        ticket = QueueTicket("expired", "old", "daily", clock.now(), clock.now()+timedelta(seconds=1))
        coordinator.store.insert("QueueTicket", ticket.ticket_id, {**ticket.to_mapping(), "status": "waiting"})
        clock.advance(2)
        sender = ControlledSender(root, clock)
        coordinator.exchange(fixture_context(), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
        self.assertEqual(coordinator.store.get("QueueTicket", "expired").value["status"], "expired")
        self.assertEqual(len(tuple(coordinator.store.scan("Coordination", {}))), 0)
        self.assertEqual(len(sender.starts), 1)

    def test_discovery_download_and_retry_all_use_finite_exchange_turns(self):
        from support import ControlledSender, fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock = Path(directory), fixture_clock()
        coordinator, _ = self.build(root, clock)
        events = self.events
        coordinator.observer = events.append
        sender = ControlledSender(root, clock, status=503)
        listing = "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json"
        download = "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/master.zip"
        coordinator.exchange(fixture_context(command="discover"), listing, sender)
        until = clock.now()+timedelta(seconds=2)
        coordinator.defer_until(until)
        coordinator.exchange(fixture_context(), download, sender)
        coordinator.exchange(replace(fixture_context(), attempt_id="retry"), download, sender)
        starts = [instant for _, instant in sender.starts]
        self.assertGreaterEqual(starts[1], until)
        self.assertTrue(all((right-left).total_seconds() >= 1/3 for left, right in zip(starts, starts[1:])))
        epochs = [event["epoch"] for event in sender.events if event["event"] == "request-start"]
        self.assertEqual(epochs, sorted(set(epochs)))
        self.assertEqual(len(epochs), 3)
        self.assertEqual(len([event for event in events if event["event"] == "release"]), 4)

    def test_unbounded_sender_exception_retains_future_guard(self):
        from support import ControlledSender, fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock = Path(directory), fixture_clock()
        coordinator, _ = self.build(root, clock)
        def unknown(cancellation, permit):
            raise RuntimeError("unknown child/drain outcome")
        sender = ControlledSender(root, clock, on_send=unknown)
        with self.assertRaises(RuntimeError):
            coordinator.exchange(fixture_context(), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
        successor, _ = self.build(root, clock)
        clock.advance(60)
        with successor.turn("new", "daily", clock.now()+timedelta(seconds=3600)) as turn:
            self.assertGreaterEqual(turn.earliest_safe, turn.handle.acquired_upper+timedelta(seconds=92))
            permit = turn.reserve("new-request")
            self.assertGreaterEqual(clock.now(), turn.earliest_safe)
            turn.complete(permit, drained=True)

    def test_one_permit_per_turn_and_no_reuse_after_complete(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("one", "backfill")
        permit = h.reserve("one")
        with self.assertRaises(OwnershipLost):
            h.turns["one"].reserve("second")
        with self.assertRaises(OwnershipLost):
            h.turns["one"].assert_current(permit)

    def test_guard_calculations_preserve_future_and_prior_uncertainty(self):
        from support import fixture_clock
        clock = fixture_clock()
        previous = clock.now()+timedelta(seconds=40)
        self.assertEqual(self.coordination.takeover_time(previous, clock.now(), 90, 2, False), clock.now()+timedelta(seconds=92))
        self.assertEqual(self.coordination.takeover_time(previous, clock.now(), 90, 2, True), previous)
        self.assertEqual(self.coordination.reservation_guard(previous, 90, 2), previous+timedelta(seconds=92))
        self.assertEqual(self.coordination.next_start(None, previous, clock.now(), 3), previous)


    def test_local_clean_release_atomically_shortens_only_after_positive_drain(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("one", "backfill")
        h.hold_request("one")
        old_guard = h.permits["one"].takeover_after
        h.finish_request("one")
        h.start("two", "daily")
        self.assertLess(h.turns["two"].earliest_safe, old_guard,
                        "A positively drained local exchange can atomically finalize journal+release")
        row = h.leases["two"].read_journal(h.turns["two"].handle)
        self.assertGreaterEqual(self.coordination.utc_value(row.value["unsafe_until"]), h.turns["two"].handle.ownership_until_upper)
        h.reserve("two")
        self.assertLess(h.starts[-1][1], clock.now()+timedelta(seconds=1))
        self.assertLess(h.starts[-1][1], old_guard)

    def test_unknown_atomic_release_stops_turn_and_retains_prior_guard(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("one", "backfill")
        h.reserve("one")
        guard = h.permits["one"].takeover_after
        def unknown():
            raise TimeoutError("atomic release outcome not confirmed")
        h.faults["one"].at("lease.before_clean_release", unknown)
        h.finish_request("one")
        self.assertTrue(h.turns["one"].cancelled.is_set())
        self.assertIsNotNone(h.turns["one"].loss_reason)
        row = h.leases["one"].read_journal(h.turns["one"].handle)
        self.assertFalse(row.value["clean_release"])
        self.assertEqual(self.coordination.utc_value(row.value["unsafe_until"]), guard)

    def test_conservative_known_and_unknown_release_preserve_guard_and_progress(self):
        from support import ControlledSender, Faults, fixture_clock
        for unknown in (False, True):
            with self.subTest(unknown=unknown):
                directory = self.enterContext(tempfile.TemporaryDirectory())
                root, clock, faults = Path(directory), fixture_clock(), Faults()
                coordinator, leases = self.build(root, clock, faults)
                # This capability shape is Azure's: journal update and release are separate operations.
                leases.release_clean = None
                if unknown:
                    def fault():
                        raise TimeoutError("release committed, acknowledgement unknown")
                    faults.at("lease.after_release", fault)
                events = []
                coordinator.observer = events.append
                sender = ControlledSender(root, clock)
                receipt = coordinator.exchange(fixture_context(), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
                self.assertEqual(receipt.error.code if receipt.error else None, "ownership_lost" if unknown else None)
                self.assertTrue(sender.cancellations[0].is_set())
                successor, _ = self.build(root, clock)
                with successor.turn("successor", "daily", clock.now()+timedelta(seconds=3600)) as turn:
                    self.assertGreaterEqual(turn.earliest_safe, turn.handle.acquired_upper+timedelta(seconds=92))
                    row = successor.leases.read_journal(turn.handle)
                    self.assertFalse(row.value["clean_release"])
                    permit = turn.reserve("after-release")
                    self.assertGreaterEqual(clock.now(), turn.earliest_safe)
                    turn.assert_current(permit)
                    turn.complete(permit, drained=True)

    def test_exchange_deadline_cancels_even_when_lease_renewals_succeed(self):
        from support import ControlledSender, fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock = Path(directory), fixture_clock()
        coordinator, _ = self.build(root, clock)
        sender = ControlledSender(root, clock, on_send=lambda cancellation, permit: clock.advance(90))
        receipt = coordinator.exchange(fixture_context(), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
        self.assertEqual(receipt.error.code, "ownership_lost")
        self.assertTrue(sender.cancellations[0].is_set())
        self.assertTrue(receipt.temporary_path.exists())

    def test_real_monitor_wakes_when_reservation_installs_short_exchange_deadline(self):
        import threading
        selected, proceed = threading.Event(), threading.Event()
        class PausedMonitorClock(self.coordination.Clock):
            paused = False
            def monotonic(self):
                instant = super().monotonic()
                if threading.current_thread().name == "sec-lease-renewal" and not self.paused:
                    self.paused = True
                    # The monitor has selected the old turn deadline before computing its wait.
                    selected.set()
                    if not proceed.wait(5):
                        raise TimeoutError("monitor barrier was not released")
                return instant
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = PausedMonitorClock()
        state, _, leases = store_bundle(Path(directory), clock=clock)
        self.addCleanup(state.close)
        self.addCleanup(leases.close)
        settings = fixture_settings(http={"exchange_deadline_seconds": 0.4})
        coordinator = self.coordination.Coordinator(settings, state, leases, clock)
        coordinator.observer = self.events.append
        try:
            with coordinator.turn("short-exchange", "daily", clock.now()+timedelta(seconds=3600)) as turn:
                self.assertTrue(selected.wait(5))
                permit = turn.reserve("short-deadline")
                self.assertLessEqual(permit.deadline_mono-clock.monotonic(), 0.4)
                proceed.set()
                self.assertTrue(turn.cancelled.wait(1),
                                "A permit deadline must wake the monitor already waiting for the 20-second renewal")
                self.assertIn("expired", turn.loss_reason)
        finally:
            proceed.set()

    def test_request_begun_just_before_finite_expiry_has_full_takeover_guard(self):
        from support import ControlledSender, Faults, fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock, faults = Path(directory), fixture_clock(), Faults()
        state, _, leases = store_bundle(root, clock=clock, observer=faults)
        self.addCleanup(state.close)
        self.addCleanup(leases.close)
        # A slow-renew fixture places the controlled start immediately before the real finite expiry.
        settings = fixture_settings(coordination={"renew_every_seconds": 59.99})
        coordinator = self.coordination.Coordinator(settings, state, leases, clock)
        with coordinator.turn("near-expiry", "backfill", clock.now()+timedelta(seconds=3600)) as turn:
            clock.advance(59)
            permit = turn.reserve("near-boundary")
            turn.assert_current(permit)
            self.assertLessEqual((turn.handle.ownership_until_upper-clock.now()).total_seconds(), 1)
            self.assertGreaterEqual(permit.takeover_after, turn.handle.ownership_until_upper+timedelta(seconds=92))
            sender = ControlledSender(root, clock, on_send=lambda cancellation, permit: clock.advance(1))
            receipt = sender.send("https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", fixture_context(), permit,
                                  cancellation=turn.cancelled)
            self.assertTrue(turn.cancelled.is_set())
            self.assertFalse(receipt.complete)

    def test_stale_epoch_refuses_socket_even_under_current_lease(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("one", "daily")
        permit = h.turns["one"].reserve("request")
        with self.assertRaises(OwnershipLost):
            h.turns["one"].assert_current(replace(permit, epoch=permit.epoch+1))
        self.assertTrue(h.turns["one"].cancelled.is_set())
        self.assertEqual(h.starts, [])


    def test_three_independent_exchange_processes_prove_intervals_priority_and_epochs(self):
        import support
        self.assertTrue(hasattr(support, "exchange_process_trace"),
                        "Three actual Coordinator.exchange processes must retain interval/ownership/priority traces")
        directory = self.enterContext(tempfile.TemporaryDirectory())
        trace = support.exchange_process_trace(Path(directory))
        starts = [event for event in trace if event["event"] == "socket-start"]
        ends = [event for event in trace if event["event"] == "socket-end"]
        self.assertEqual([event["worker"] for event in starts], ["backfill", "daily", "reconciliation", "backfill"])
        self.assertEqual(len({event["pid"] for event in starts}), 3)
        self.assertEqual(len(starts), len(ends))
        for previous, current in zip(starts, starts[1:]):
            self.assertGreaterEqual(current["logical_mono"]-previous["logical_mono"], 1/3)
        for start in starts:
            end = next(event for event in ends if event["request_id"] == start["request_id"])
            self.assertLessEqual(end["logical_mono"], start["deadline_mono"])
            self.assertEqual(start["epoch"], start["journal_epoch"])
            self.assertEqual(start["owner"], start["journal_owner"])
            self.assertFalse(start["cancelled"])
            self.assertLess(start["logical_mono"], start["start_before_mono"])
        intervals = sorted((start["logical_mono"], next(event["logical_mono"] for event in ends if event["request_id"] == start["request_id"])) for start in starts)
        self.assertTrue(all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:])))
        self.assertEqual([event["epoch"] for event in starts], sorted({event["epoch"] for event in starts}))
        choices = [event for event in trace if event["event"] == "queue-choice"]
        self.assertTrue(any(event.get("priority") == "daily" for event in choices))
        self.assertEqual(len([event for event in trace if event["event"] == "acquire"]), 4)
        self.assertEqual(len([event for event in trace if event["event"] == "release"]), 4)
        self.assertFalse(any(event["event"] in ("process-error", "loss") for event in trace))
        support.retain_coordination_trace("three-process-exchange.json", trace)


    def test_storage_latency_cannot_undercount_latest_permitted_dispatch(self):
        from support import fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        clock = fixture_clock()
        h = self.harness(Path(directory), clock)
        self.addCleanup(h.close)
        h.start("one", "backfill")
        h.faults["one"].at("journal.after_read", lambda: clock.advance(0.2))
        permit = h.turns["one"].reserve("delayed-storage")
        clock.advance(permit.start_before_mono-clock.monotonic()-0.00001)
        h.dispatch("one", permit)
        h.finish_request("one")
        h.start("two", "daily")
        h.reserve("two")
        spacing = (h.starts[1][1]-h.starts[0][1]).total_seconds()
        self.assertGreaterEqual(spacing, 1/3,
                                "Storage latency between clock observation and durable reservation must not create a compressed transport interval")

    def test_queue_storage_outage_after_drain_retains_partial_receipt(self):
        from support import ControlledSender, Faults, fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock, faults = Path(directory), fixture_clock(), Faults()
        coordinator, _ = self.build(root, clock, faults)
        def outage():
            raise OSError("ticket status acknowledgement unknown")
        faults.at("state.after_replace", outage)
        sender = ControlledSender(root, clock)
        try:
            receipt = coordinator.exchange(fixture_context(), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
        except OSError as error:
            self.fail(f"A queue outage after positive sender drain must preserve the returned receipt: {error}")
        self.assertFalse(receipt.complete)
        self.assertEqual(receipt.error.code, "ownership_lost")
        self.assertTrue(receipt.temporary_path.exists())
        self.assertTrue(sender.cancellations[0].is_set())


    def test_full_exchange_after_unknown_renewal_waits_confirmed_successor_guard(self):
        from support import ControlledSender, Faults, fixture_clock
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock, faults = Path(directory), fixture_clock(), Faults()
        old, _ = self.build(root, clock, faults)
        def unknown():
            raise TimeoutError("renewal committed but acknowledgement lost")
        faults.at("lease.after_renew", unknown)
        old_sender = ControlledSender(root, clock, on_send=lambda cancellation, permit: clock.advance(20))
        old_receipt = old.exchange(replace(fixture_context(), execution_id="old"), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", old_sender)
        self.assertEqual(old_receipt.error.code, "ownership_lost")
        self.assertTrue(old_sender.cancellations[0].is_set())
        clock.advance(60)
        successor, _ = self.build(root, clock)
        sender = ControlledSender(root, clock)
        receipt = successor.exchange(replace(fixture_context(priority="daily"), execution_id="new"), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
        self.assertTrue(receipt.complete)
        acquired = [event for event in self.events if event["event"] == "acquire" and event["owner"].startswith("new:")][0]
        acquired_at = self.coordination.utc_value(acquired["at"])
        self.assertGreaterEqual(sender.starts[0][1], acquired_at+timedelta(seconds=92))
        self.assertLessEqual(old_sender.ends[0][1], sender.starts[0][1])
        self.assertTrue(old_receipt.temporary_path.exists())

    def test_shared_cancellation_event_reaches_spawned_transport_child(self):
        import multiprocessing
        from support import ControlledSender, Faults, fixture_clock, cancellation_child
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root, clock, faults = Path(directory), fixture_clock(), Faults()
        coordinator, _ = self.build(root, clock, faults)
        def unknown():
            raise TimeoutError("unknown renewal during child body stream")
        faults.at("lease.after_renew", unknown)
        context = multiprocessing.get_context("spawn")
        ready, returned = context.Event(), context.Queue()
        def stream(cancellation, permit):
            process = context.Process(target=cancellation_child, args=(cancellation, ready, returned))
            process.start()
            try:
                self.assertTrue(ready.wait(5))
                clock.advance(20)
                outcome = returned.get(timeout=5)
                self.assertTrue(outcome["cancelled"])
                process.join(5)
                self.assertEqual(process.exitcode, 0)
            finally:
                if process.is_alive():
                    process.terminate()
                    process.join(5)
                returned.close()
                returned.join_thread()
        sender = ControlledSender(root, clock, on_send=stream)
        receipt = coordinator.exchange(fixture_context(), "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
        self.assertEqual(receipt.error.code, "ownership_lost")
        self.assertTrue(receipt.temporary_path.exists())
