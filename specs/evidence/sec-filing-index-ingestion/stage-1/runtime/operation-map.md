# Compatibility probe operation map

The minimal SDK set maps the accepted contract capabilities to Identity managed-identity token support, Blob content read/write and immutable-object conditions/lease support, and Tables entity read/conditional write support. This map selects synchronous Requests as the SEC transport candidate and PyArrow for synthetic Parquet serialization. The probe exercises imports and local serialization only: it does not instantiate credentials, acquire tokens, create clients or call Azure data APIs.

No selected capability in this probe requires DFS-only path rename, ACL, filesystem or directory APIs. `azure-storage-file-datalake` is therefore omitted. HNS alone does not force a DFS dependency. The production per-object write-lifecycle API decision is not finalized by this compatibility investigation; Task 5 must retain the Blob/DFS mixing restrictions in the previously collected ADLS provider documentation. If an accepted operation selection later requires DFS, this exact minimal combination does not certify it and its added dependency must be resolved and re-probed.

The map adds no production implementation, API-per-object lifecycle design or Azure access claim. Authority remains the parent contract and the recorded provider limitations.
