"""I/O boundary marker for repository adapters.

Filesystem ingestion remains owned by backend.app.ingest; this module keeps
the engine independent of storage and prevents hidden data repair.
"""
