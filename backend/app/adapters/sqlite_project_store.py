import sqlite3
from contextlib import closing
from pathlib import Path
from threading import Lock
from uuid import UUID

from app.domain.project import Project


class SQLiteProjectStore:
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
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

    def save(self, project: Project) -> None:
        payload = project.model_dump_json()
        with self._lock, closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO projects (id, payload, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        payload = excluded.payload,
                        updated_at = excluded.updated_at
                    """,
                    (str(project.id), payload, project.updated_at.isoformat()),
                )

    def get(self, project_id: UUID) -> Project | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM projects WHERE id = ?", (str(project_id),)
            ).fetchone()
        return Project.model_validate_json(row["payload"]) if row else None

    def list(self) -> list[Project]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT payload FROM projects ORDER BY updated_at DESC"
            ).fetchall()
        return [Project.model_validate_json(row["payload"]) for row in rows]

