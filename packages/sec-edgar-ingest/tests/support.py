"""Validated builders shared by offline acquisition tests."""
import json
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sec_edgar_ingest.config import Settings
    from sec_edgar_ingest.models import RunContext, Source, SourceWorkset, Snapshot
    from sec_edgar_ingest.storage.contracts import StateStore, ObjectStore, LeaseStore, BoundaryObserver

FIXTURE_CONFIG = Path(__file__).parent / "fixtures/config/local.json"


def fixture_settings(**overrides: object) -> "Settings":
    from sec_edgar_ingest.config import Settings
    value = json.loads(FIXTURE_CONFIG.read_text())
    for key, override in overrides.items():
        if isinstance(override, dict) and isinstance(value.get(key), dict):
            value[key].update(override)
        else:
            value[key] = override
    return Settings.from_mapping(value)


def fixture_context(command: str = "collect", priority: str = "backfill") -> "RunContext":
    from sec_edgar_ingest.config import pin_context
    from sec_edgar_ingest.models import RunContext
    settings = fixture_settings()
    started = datetime(2026, 10, 6, tzinfo=timezone.utc)
    context = RunContext(
        run_id="fixture-run", execution_id="fixture-execution", command=command,
        attempt_id="fixture-attempt", image_digest=settings.worker.image_digest,
        parser_version=settings.etl.parser_version, schema_version=settings.etl.schema_version,
        config_sha256=settings.config_sha256, started_at=started,
        deadline=started + timedelta(seconds=3600), priority=priority,
    )
    return pin_context(settings, context, date(2026, 10, 6))[0]


def fixture_source(period: str = "2015Q1", kind: str = "quarterly") -> "Source":
    from sec_edgar_ingest.models import Source
    from sec_edgar_ingest.urls import child_url, source_id
    if kind == "quarterly":
        year, quarter = period.split("Q")
        parent = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/index.json"
        name, representation = "master.zip", "zip"
    else:
        day = date.fromisoformat(period)
        quarter = (day.month - 1) // 3 + 1
        parent = f"https://www.sec.gov/Archives/edgar/daily-index/{day.year}/QTR{quarter}/index.json"
        name, representation = f"master.{day:%Y%m%d}.idx", "idx"
    url = child_url(parent, name, name, False)
    return Source(source_id(url), url, kind, period, representation)


def fixture_workset(members: tuple["Source", ...], discovery_complete: bool = True) -> "SourceWorkset":
    from sec_edgar_ingest.models import DirectoryOutcome, Error
    from sec_edgar_ingest.worksets import make_source_workset
    by_directory = {}
    for source in members:
        url = source.canonical_url.rsplit("/", 1)[0] + "/index.json"
        by_directory.setdefault(url, []).append(source)
    if not by_directory:
        by_directory["https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json"] = []
    directories = tuple(
        DirectoryOutcome(url, group[0].period if group else "2015Q1",
                         "available" if group else "no_new_sources", "a" * 64,
                         tuple(member.source_id for member in group), None)
        for url, group in by_directory.items()
    )
    if not discovery_complete:
        failed = DirectoryOutcome(
            "https://www.sec.gov/Archives/edgar/full-index/2015/QTR2/index.json",
            "2015Q2", "discovery_failed", None, (), Error("listing", "failed", True, None, {}),
        )
        directories += (failed,)
    return make_source_workset(fixture_context(), "2026Q4", "fixture-discovery",
                               tuple(members), directories, date(2026, 10, 1))


def fixture_snapshot(source: "Source", body: bytes) -> "Snapshot":
    import hashlib
    from sec_edgar_ingest.models import Snapshot, QUARTERLY_ENVELOPE_VERSION, DAILY_ENVELOPE_VERSION
    digest = hashlib.sha256(body).hexdigest()
    envelope = QUARTERLY_ENVELOPE_VERSION if source.kind == "quarterly" else DAILY_ENVELOPE_VERSION
    return Snapshot(source.source_id, digest,
                    f"raw/sec/indexes/kind={source.kind}/period={source.period}/sha256={digest}/master.{source.representation}",
                    len(body), fixture_context().started_at, {}, source.representation, envelope)


class Faults:
    """One-shot observers interrupt the real durable transition at a named boundary."""
    def __init__(self):
        self._actions = {}

    def at(self, point: str, action: Callable[[], None]) -> None:
        self._actions[point] = action

    def __call__(self, point: str) -> None:
        action = self._actions.pop(point, None)
        if action is not None:
            action()


class FixtureClock:
    def __init__(self):
        self.instant = datetime(2026, 10, 6, tzinfo=timezone.utc)
        self.elapsed = 0.0

    def now(self) -> datetime:
        return self.instant

    def monotonic(self) -> float:
        return self.elapsed

    def advance(self, seconds: float) -> None:
        self.instant += timedelta(seconds=seconds)
        self.elapsed += seconds


def store_bundle(root: Path, *, observer: "BoundaryObserver | None" = None, clock=None) -> tuple["StateStore", "ObjectStore", "LeaseStore"]:
    from sec_edgar_ingest.storage.local import LocalStateStore, LocalObjectStore, LocalLeaseStore
    return (LocalStateStore(root, observer=observer), LocalObjectStore(root, observer=observer),
            LocalLeaseStore(root, observer=observer, clock=clock))


# Task 4 controls drive real coordinators/stores; they own no alternate scheduling state.
def fixture_clock():
    from sec_edgar_ingest.coordination import ManualClock
    return ManualClock(datetime(2026, 10, 6, tzinfo=timezone.utc))


class ControlledSender:
    """Record actual controlled transport starts; returning a receipt proves this send drained."""
    def __init__(self, root, clock, *, on_send=None, status=200):
        self.root, self.clock, self.on_send, self.status = Path(root), clock, on_send, status
        self.starts, self.ends, self.events = [], [], []
        self.active = self.maximum_active = 0
        self.cancellations = []

    def send(self, url, context, permit, *, cancellation):
        import hashlib
        import uuid
        from sec_edgar_ingest.models import BodyReceipt, Error
        from sec_edgar_ingest.storage.contracts import OwnershipLost
        if cancellation.is_set() or self.clock.monotonic() >= permit.start_before_mono:
            raise OwnershipLost("controlled socket refuses cancelled/late dispatch")
        instant = self.clock.now()
        self.starts.append((permit.owner_id, instant))
        self.events.append({"event": "request-start", "at": instant.isoformat(), "epoch": permit.epoch,
                            "owner": permit.owner_id, "request_id": permit.request_id})
        self.cancellations.append(cancellation)
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            if self.on_send is not None:
                self.on_send(cancellation, permit)
        finally:
            self.active -= 1
            end = self.clock.now()
            self.ends.append((permit.owner_id, end))
            self.events.append({"event": "request-end", "at": end.isoformat(), "epoch": permit.epoch,
                                "owner": permit.owner_id, "request_id": permit.request_id})
        path = self.root / ("receipt-"+uuid.uuid4().hex)
        body = b"bounded offline partial" if cancellation.is_set() else b"bounded offline response"
        path.write_bytes(body)
        error = Error("cancelled", "controlled exchange drained after cancellation", True, None, {}) if cancellation.is_set() else None
        return BodyReceipt(url, self.status, {}, path, self.clock.now(), len(body), hashlib.sha256(body).hexdigest(),
                           error is None, error)


class CoordinationHarness:
    def __init__(self, root, clock):
        self.root, self.clock = Path(root), clock
        self.coordinators, self.turns, self.contexts, self.leases, self.faults, self.permits = {}, {}, {}, {}, {}, {}
        self.starts, self.events, self.active = [], [], set()
        self.maximum_active = 0

    def start(self, owner, priority):
        from sec_edgar_ingest.coordination import Coordinator
        faults = Faults()
        state, _, leases = store_bundle(self.root, clock=self.clock, observer=faults)
        self.faults[owner], self.leases[owner] = faults, leases
        coordinator = Coordinator(fixture_settings(), state, leases, self.clock)
        coordinator.observer = self.events.append
        self.coordinators[owner] = coordinator
        context = coordinator.turn(owner, priority, self.clock.now()+timedelta(seconds=3600))
        self.contexts[owner] = context
        self.turns[owner] = context.__enter__()

    def reserve(self, owner):
        permit = self.turns[owner].reserve(owner+"-request")
        self.permits[owner] = permit
        self.dispatch(owner, permit)
        return permit

    def hold_request(self, owner):
        return self.reserve(owner)

    def dispatch(self, owner, permit):
        self.turns[owner].assert_current(permit)
        if self.clock.monotonic() >= permit.start_before_mono:
            raise AssertionError("harness socket would dispatch late")
        self.permits[owner] = permit
        self.starts.append((owner, self.clock.now()))
        self.events.append({"event": "request-start", "owner": owner, "epoch": permit.epoch,
                            "at": self.clock.now().isoformat()})
        self.active.add(owner)
        self.maximum_active = max(self.maximum_active, len(self.active))

    def expire_owner(self, owner):
        until = self.turns[owner].handle.ownership_until_upper
        context = self.contexts.pop(owner)
        context.__exit__(RuntimeError, RuntimeError("fixture parent abandoned the bounded sender"), None)
        self.clock.advance(max(0, (until-self.clock.now()).total_seconds()))
        if not self.turns[owner].cancelled.is_set():
            raise AssertionError("expired ownership did not cancel the real turn")

    def finish_request(self, owner):
        from sec_edgar_ingest.storage.contracts import OwnershipLost
        self.active.discard(owner)
        self.events.append({"event": "request-end", "owner": owner, "epoch": self.permits[owner].epoch,
                            "at": self.clock.now().isoformat()})
        try:
            self.turns[owner].complete(self.permits[owner], drained=True)
        except OwnershipLost:
            pass
        context = self.contexts.pop(owner, None)
        if context is not None:
            context.__exit__(None, None, None)

    def acquire_successor(self, owner):
        self.start(owner, "daily")

    def close(self):
        if hasattr(self, "trace_name"):
            retain_coordination_trace(self.trace_name, self.events)
        for context in tuple(self.contexts.values()):
            context.__exit__(RuntimeError, RuntimeError("fixture cleanup retains guard"), None)
        self.contexts.clear()
        for coordinator in self.coordinators.values():
            coordinator.store.close()
        for leases in self.leases.values():
            leases.close()


def coordination_harness(root: Path, *, clock):
    return CoordinationHarness(root, clock)


def retain_coordination_trace(name, events):
    import os
    destination = os.environ.get("SEC_EDGAR_TASK4_TRACE_DIR")
    if destination:
        root = Path(destination)
        root.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(json.dumps(events, indent=2, sort_keys=True)+"\n")


class ProcessClock:
    """Shared logical time moves only when every exchange process is parked at a barrier."""
    def __init__(self, value, condition, recorder=None):
        self.value, self.condition, self.recorder = value, condition, recorder

    def now(self):
        return datetime(2026, 10, 6, tzinfo=timezone.utc)+timedelta(seconds=self.monotonic())

    def monotonic(self):
        with self.condition:
            return self.value.value

    def sleep(self, seconds):
        target = self.monotonic()+seconds
        self.recorder.emit("clock-wait", target=target)
        with self.condition:
            if not self.condition.wait_for(lambda: self.value.value >= target, timeout=10):
                raise TimeoutError("parent did not advance shared logical clock")
        self.recorder.emit("clock-awake")

    def subscribe(self, callback):
        import threading
        stopped = threading.Event()
        def monitor():
            observed = self.monotonic()
            while not stopped.is_set():
                with self.condition:
                    changed = self.condition.wait_for(lambda: stopped.is_set() or self.value.value != observed, timeout=10)
                    observed = self.value.value
                if changed and not stopped.is_set():
                    callback()
        thread = threading.Thread(target=monitor, name="fixture-logical-renewal", daemon=True)
        thread.start()
        def unsubscribe():
            stopped.set()
            with self.condition:
                self.condition.notify_all()
            thread.join(2)
        return unsubscribe


class ProcessRecorder:
    def __init__(self, worker, clock, queue, lock, sequence):
        self.worker, self.clock, self.queue, self.lock, self.sequence = worker, clock, queue, lock, sequence

    def emit(self, event, **details):
        import os
        import time
        with self.lock:
            self.sequence.value += 1
            self.queue.put({"sequence": self.sequence.value, "event": event, "worker": self.worker,
                            "pid": os.getpid(), "logical_at": self.clock.now().isoformat(),
                            "logical_mono": self.clock.monotonic(), "real_monotonic_ns": time.monotonic_ns(), **details})

    def observe(self, event):
        details = dict(event)
        kind = details.pop("event")
        self.emit(kind, **details)


class ProcessSender:
    def __init__(self, root, clock, coordinator, recorder, status):
        self.root, self.clock, self.coordinator, self.recorder, self.status = root, clock, coordinator, recorder, status

    def send(self, url, context, permit, *, cancellation):
        import hashlib
        from sec_edgar_ingest.models import BodyReceipt
        from sec_edgar_ingest.storage.contracts import OwnershipLost
        if cancellation.is_set() or self.clock.monotonic() >= permit.start_before_mono:
            raise OwnershipLost("process controlled socket refuses stale permit")
        turn = self.coordinator._active
        row = self.coordinator.leases.read_journal(turn.handle)
        if row.value["owner_id"] != permit.owner_id or row.value["epoch"] != permit.epoch:
            raise OwnershipLost("process transport observes a replaced sentinel epoch")
        self.recorder.emit("socket-start", owner=permit.owner_id, epoch=permit.epoch, request_id=permit.request_id,
                           journal_epoch=row.value["epoch"], journal_owner=row.value["owner_id"],
                           lease_id=turn.handle.lease_id, start_before_mono=permit.start_before_mono,
                           deadline_mono=permit.deadline_mono, cancelled=cancellation.is_set(), status=self.status)
        if self.status == 503:
            self.coordinator.defer_until(self.clock.now()+timedelta(seconds=2))
        self.clock.sleep(0.1)
        self.recorder.emit("socket-end", owner=permit.owner_id, epoch=permit.epoch, request_id=permit.request_id)
        if cancellation.is_set():
            raise OwnershipLost("process controlled exchange unexpectedly lost ownership")
        body = b"bounded independent process response"
        path = self.root / ("process-receipt-"+permit.request_id)
        path.write_bytes(body)
        return BodyReceipt(url, self.status, {"Retry-After": "2"} if self.status == 503 else {}, path,
                           self.clock.now(), len(body), hashlib.sha256(body).hexdigest(), True, None)


def _exchange_process(root, worker, value, condition, queue, lock, sequence, begin):
    from dataclasses import replace
    import traceback
    from sec_edgar_ingest.coordination import Coordinator
    root = Path(root)
    clock = ProcessClock(value, condition)
    recorder = ProcessRecorder(worker, clock, queue, lock, sequence)
    clock.recorder = recorder
    state = leases = None
    try:
        state, _, leases = store_bundle(root, clock=clock)
        coordinator = Coordinator(fixture_settings(), state, leases, clock)
        coordinator.observer = recorder.observe
        recorder.emit("ready")
        if not begin.wait(10):
            raise TimeoutError("parent did not release process launch barrier")
        exchanges = 2 if worker == "backfill" else 1
        for ordinal in range(exchanges):
            context = replace(fixture_context(priority=worker), execution_id=worker, attempt_id=f"{worker}-{ordinal}")
            sender = ProcessSender(root, clock, coordinator, recorder, 503 if worker == "backfill" and ordinal == 0 else 200)
            receipt = coordinator.exchange(context, "https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/index.json", sender)
            if not receipt.complete:
                raise AssertionError(receipt.error)
            recorder.emit("exchange-return", attempt=ordinal, status=receipt.status)
    except BaseException:
        recorder.emit("process-error", traceback=traceback.format_exc())
    finally:
        if state is not None:
            state.close()
        if leases is not None:
            leases.close()
        recorder.emit("done")


def exchange_process_trace(root):
    import multiprocessing
    context = multiprocessing.get_context("spawn")
    condition, value = context.Condition(), context.Value("d", 0)
    queue, lock, sequence = context.Queue(), context.Lock(), context.Value("i", 0)
    names = ("backfill", "daily", "reconciliation")
    begins = {name: context.Event() for name in names}
    processes = [context.Process(target=_exchange_process, args=(str(root), name, value, condition, queue, lock, sequence, begins[name])) for name in names]
    records, ready, done, waiting = [], set(), set(), {}
    states = {name: "not-started" for name in names}
    contenders_started = False
    try:
        for process in processes:
            process.start()
        while len(ready) < 3:
            event = queue.get(timeout=10)
            records.append(event)
            if event["event"] == "process-error":
                raise AssertionError(event["traceback"])
            if event["event"] == "ready":
                ready.add(event["worker"])
        begins["backfill"].set()
        states["backfill"] = "running"
        steps = 0
        while len(done) < 3:
            event = queue.get(timeout=10)
            records.append(event)
            worker, kind = event["worker"], event["event"]
            if kind == "process-error":
                raise AssertionError(event["traceback"])
            if kind == "socket-start" and worker == "backfill" and not contenders_started:
                for contender in ("daily", "reconciliation"):
                    states[contender] = "running"
                    begins[contender].set()
                contenders_started = True
            if kind == "clock-wait":
                waiting[worker], states[worker] = event["target"], "waiting"
            elif kind == "clock-awake":
                waiting.pop(worker, None)
                states[worker] = "running"
            elif kind == "done":
                done.add(worker)
                waiting.pop(worker, None)
                states[worker] = "done"
            if contenders_started and waiting and all(state in ("waiting", "done") for state in states.values()):
                target = min(waiting.values())
                for name, instant in tuple(waiting.items()):
                    if instant <= target:
                        states[name] = "waking"
                with condition:
                    value.value = max(value.value, target)
                    condition.notify_all()
                steps += 1
                if steps > 1000:
                    raise AssertionError("logical process barriers did not make bounded progress")
        for process in processes:
            process.join(10)
            if process.exitcode != 0:
                raise AssertionError(f"independent exchange process exited {process.exitcode}")
        return sorted(records, key=lambda event: event["sequence"])
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(10)
        queue.close()
        queue.join_thread()



def cancellation_child(cancellation, ready, returned):
    import os
    ready.set()
    returned.put({"pid": os.getpid(), "cancelled": cancellation.wait(5)})


def _constructor_process(root, begin, queue):
    import os
    import time
    import traceback
    state = leases = None
    queue.put({"event": "ready", "pid": os.getpid(), "real_monotonic_ns": time.monotonic_ns()})
    try:
        if not begin.wait(10):
            raise TimeoutError("constructor launch barrier did not open")
        state, _, leases = store_bundle(Path(root), clock=FixtureClock())
        state.insert("QueueTicket", "startup-"+str(os.getpid()), {"pid": os.getpid()})
        queue.put({"event": "constructed", "pid": os.getpid(), "real_monotonic_ns": time.monotonic_ns()})
    except BaseException:
        queue.put({"event": "constructor-error", "pid": os.getpid(), "traceback": traceback.format_exc()})
    finally:
        if state is not None:
            state.close()
        if leases is not None:
            leases.close()


def constructor_process_probe(root):
    import multiprocessing
    context = multiprocessing.get_context("spawn")
    begin, queue = context.Event(), context.Queue()
    processes = [context.Process(target=_constructor_process, args=(str(root), begin, queue)) for _ in range(3)]
    records = []
    try:
        for process in processes:
            process.start()
        for _ in processes:
            event = queue.get(timeout=10)
            records.append(event)
            if event["event"] != "ready":
                raise AssertionError(event)
        begin.set()
        for _ in processes:
            event = queue.get(timeout=10)
            records.append(event)
            if event["event"] != "constructed":
                raise AssertionError(event)
        for process in processes:
            process.join(10)
            if process.exitcode != 0:
                raise AssertionError(f"constructor process exited {process.exitcode}")
        return records
    finally:
        retain_coordination_trace("initialized-root-constructor-probe.json", records)
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(10)
        queue.close()
        queue.join_thread()
