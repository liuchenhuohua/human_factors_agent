import sqlite3
from contextlib import closing
from pathlib import Path
from threading import Lock
from uuid import UUID

from app.domain.experiment import ExperimentPlan


class SQLiteExperimentStore:
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
                    CREATE TABLE IF NOT EXISTS experiment_plans (
                        project_id TEXT PRIMARY KEY,
                        payload TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

    def save(self, plan: ExperimentPlan) -> None:
        with self._lock, closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO experiment_plans (project_id, payload, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        payload = excluded.payload,
                        updated_at = excluded.updated_at
                    """,
                    (
                        str(plan.project_id),
                        plan.model_dump_json(),
                        plan.updated_at.isoformat(),
                    ),
                )

    def get_by_project(self, project_id: UUID) -> ExperimentPlan | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM experiment_plans WHERE project_id = ?",
                (str(project_id),),
            ).fetchone()
        return ExperimentPlan.model_validate_json(row["payload"]) if row else None
