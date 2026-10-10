"""Bounded public catalogue paging and fingerprint-based incremental upserts."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json

import httpx

from app.integrations.sphere_catalog import convert_sphere_record
from app.utils.dates import parse_date


@dataclass
class SyncReport:
    source_endpoint: str
    page_size: int
    mode: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pages: int = 0
    source_records_observed: int = 0
    source_count: int | None = None
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    upserted: int = 0
    unchanged: int = 0
    deleted: int = 0
    index_document_count: int = 0
    failures: list[str] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)


class SyncFailure(RuntimeError):
    def __init__(self, report: SyncReport):
        super().__init__("Catalogue sync failed: " + "; ".join(report.failures))
        self.report = report


class SpherePublicClient:
    def __init__(self, endpoint: str, *, client=None, timeout: float = 20,
                 max_response_bytes: int = 16 * 1024 * 1024):
        url = httpx.URL(endpoint)
        if url.scheme not in {"http", "https"} or not url.host or url.username or url.password:
            raise ValueError("Configure a public HTTP(S) catalogue endpoint without credentials")
        if not 0 < timeout <= 60:
            raise ValueError("Source timeout must be between 0 and 60 seconds")
        self.endpoint = endpoint
        self.client = client or httpx.Client(timeout=timeout, follow_redirects=False)
        self.max_response_bytes = max_response_bytes

    def page(self, limit: int, offset: int):
        body = {"request": {"filters": {"primaryCategory": ["Course"], "status": ["Live"]},
                            "limit": limit, "offset": offset}}
        with self.client.stream("POST", self.endpoint, json=body) as response:
            response.raise_for_status()
            payload = bytearray()
            for chunk in response.iter_bytes():
                payload.extend(chunk)
                if len(payload) > self.max_response_bytes:
                    raise ValueError("Source response exceeds byte limit")
        return json.loads(payload)


def sync_catalogue(source, backend, *, page_size=100, mode="full", max_pages=1000) -> SyncReport:
    if type(page_size) is not int or not 1 <= page_size <= 100 or mode not in {"full", "incremental"}:
        raise ValueError("Sync needs page_size 1..100 and mode full or incremental")
    report = SyncReport(source.endpoint, page_size, mode)
    documents = {}
    seen = set()
    page_signatures = set()
    try:
        for page in range(max_pages):
            payload = source.page(page_size, report.source_records_observed)
            report.pages += 1
            if not isinstance(payload, dict) or payload.get("responseCode", "OK") != "OK":
                raise ValueError("Unexpected source response envelope")
            result = payload.get("result")
            if not isinstance(result, dict) or not isinstance(result.get("content"), list):
                raise ValueError("Source result.content must be an array")
            records = result["content"]
            count = result.get("count")
            if count is not None:
                if type(count) is not int or count < 0:
                    raise ValueError("Source count must be a nonnegative integer")
                if report.source_count is not None and count != report.source_count:
                    raise ValueError("Source count changed during paging; rerun sync")
                report.source_count = count
            if len(records) > page_size:
                raise ValueError("Source ignored requested page size")
            signature = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
            if records and signature in page_signatures:
                raise ValueError("Source repeated a page; offset may be ignored")
            page_signatures.add(signature)
            for record in records:
                index = report.source_records_observed
                report.source_records_observed += 1
                document, diagnostics = convert_sphere_record(record, index)
                report.diagnostics.extend(d.model_dump(exclude_none=True) for d in diagnostics)
                if document is None:
                    report.rejected += 1
                    continue
                if document.category != "Course" or document.publication_status != "Live":
                    raise ValueError("Source returned a record outside Live Course filters")
                if document.updated_on:
                    try:
                        parse_date(document.updated_on)
                    except ValueError:
                        report.rejected += 1
                        report.diagnostics.append({"code": "invalid_updated_on", "identifier": document.course_id})
                        continue
                fingerprint = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False,
                                                        separators=(",", ":")).encode()).hexdigest()
                if document.course_id in seen:
                    report.duplicates += 1
                    if documents[document.course_id].metadata["source_fingerprint"] != fingerprint:
                        raise ValueError("Conflicting duplicate source ID")
                    continue
                seen.add(document.course_id)
                document.metadata["source_fingerprint"] = fingerprint
                documents[document.course_id] = document
                report.accepted += 1
            if report.source_count is not None and report.source_records_observed > report.source_count:
                raise ValueError("Source records exceed reported count")
            if len(records) < page_size:
                if report.source_count is not None and report.source_records_observed != report.source_count:
                    raise ValueError("Source exhausted before its reported count")
                break
        else:
            raise ValueError("Source exceeded maximum page count")
        existing = {d.course_id: d for d in backend.all_documents()}
        changed = [d for d in documents.values() if mode == "full" or d.course_id not in existing
                   or existing[d.course_id].metadata.get("source_fingerprint") != d.metadata["source_fingerprint"]]
        report.unchanged = report.accepted - len(changed)
        report.upserted = backend.bulk_upsert(changed)
        # Only remove stale source-owned documents after a complete, rejection-free traversal.
        stale = [key for key, doc in existing.items() if "source_fingerprint" in doc.metadata and key not in seen]
        if not report.rejected:
            report.deleted = backend.delete_many(stale)
        report.index_document_count = backend.document_count()
        if hasattr(backend, "health_details"):
            details = backend.health_details()
            report.index_document_count = details.get("index_document_count", report.index_document_count)
            if details.get("status") != "up":
                raise RuntimeError("Index count or readiness reconciliation failed")
    except Exception as exc:
        # Avoid logging URLs, upstream bodies, or credentials in exception text.
        report.failures.append(str(exc) if isinstance(exc, ValueError) else type(exc).__name__)
        report.index_document_count = backend.document_count()
        raise SyncFailure(report) from exc
    return report
