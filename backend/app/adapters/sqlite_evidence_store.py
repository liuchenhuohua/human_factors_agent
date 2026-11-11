import sqlite3
from contextlib import closing
from pathlib import Path
from threading import Lock
from uuid import UUID

from app.domain.evidence import EvidenceReview


class SQLiteEvidenceStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS evidence_reviews (
                        project_id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

    def save(self, review: EvidenceReview) -> None:
        with self._lock, closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO evidence_reviews (project_id, payload, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        payload = excluded.payload,
                        updated_at = excluded.updated_at
                    """,
                    (
                        str(review.project_id),
                        review.model_dump_json(),
                        review.updated_at.isoformat(),
                    ),
                )

    def get_by_project(self, project_id: UUID) -> EvidenceReview | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM evidence_reviews WHERE project_id = ?",
                (str(project_id),),
            ).fetchone()
        return EvidenceReview.model_validate_json(row["payload"]) if row else None
