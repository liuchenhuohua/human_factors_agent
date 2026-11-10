from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.config import settings
from app.transport.http import create_router
from app.workflows.project_workflow import ProjectWorkflow


def create_app() -> FastAPI:
    store = SQLiteProjectStore(settings.database_path)
    workflow = ProjectWorkflow(RuleBasedProblemFramer(), store)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_router(workflow), prefix="/api")
    return app


app = create_app()

