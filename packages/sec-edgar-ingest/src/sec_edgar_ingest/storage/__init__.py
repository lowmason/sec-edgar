"""Open one validated deployment's durable state, immutable objects and fixed lease."""
from pathlib import Path

from ..config import Settings
from .contracts import (AlreadyExists, ClockUncertain, Conflict, LeaseHandle, LeaseStore,
                        ObjectStore, OwnershipLost, StateStore, BoundaryObserver, deployment_binding)


def open_stores(settings: Settings, *, base_path: Path | None = None, observer: BoundaryObserver | None = None) -> tuple[StateStore, ObjectStore, LeaseStore]:
    validated = Settings.from_mapping(settings.to_mapping())
    if validated.storage.backend == "local-fixture":
        from .local import LocalLeaseStore, LocalObjectStore, LocalStateStore
        root = (base_path if base_path is not None else Path.cwd()) / validated.storage.root
        binding = deployment_binding(validated, root=root)
        objects = LocalObjectStore(root, observer=observer, binding=binding)
        state = LocalStateStore(root, observer=observer, binding=binding)
        leases = LocalLeaseStore(root, observer=observer, binding=binding)
        return state, objects, leases
    from .azure import open_azure_stores
    return open_azure_stores(validated, observer=observer)
