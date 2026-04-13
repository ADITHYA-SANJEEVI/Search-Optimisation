"""Document indexing service."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.core.errors import ServiceError
from app.schemas.indexing import CourseDocumentPayload
from app.search.backend import InMemorySearchBackend


class IndexService:
    def __init__(self, backend: InMemorySearchBackend) -> None:
        self.backend = backend

    def bulk_index(self, documents: list[CourseDocumentPayload]) -> int:
        if not documents:
            raise ServiceError("empty_index_request", "No documents provided for bulk indexing", status_code=400)
        return self.backend.bulk_upsert(documents)

    def update(self, document: CourseDocumentPayload) -> None:
        self.backend.upsert_one(document)

    def delete(self, course_ids: list[str]) -> int:
        if not course_ids:
            raise ServiceError("empty_delete_request", "No course ids supplied", status_code=400)
        return self.backend.delete_many(course_ids)

    def reindex(self, documents: list[CourseDocumentPayload], reload_sample_data: bool) -> int:
        existing_ids = [document.course_id for document in self.backend.all_documents()]
        if existing_ids:
            self.backend.delete_many(existing_ids)
        indexed = 0
        if reload_sample_data:
            indexed += self.load_sample_data()
        if documents:
            indexed += self.bulk_index(documents)
        return indexed

    def load_sample_data(self, path: str | None = None) -> int:
        file_path = Path(path or settings.sample_data_path)
        if not file_path.exists():
            raise ServiceError(
                "sample_data_missing",
                "Configured sample data file was not found",
                status_code=500,
                details={"path": str(file_path)},
            )
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        documents = [CourseDocumentPayload(**item) for item in payload]
        return self.bulk_index(documents)
