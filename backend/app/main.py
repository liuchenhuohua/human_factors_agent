import os
import sqlite3
from contextlib import asynccontextmanager

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver

from app.adapters.openai_problem_framer import (
    OpenAIProblemFramer,
    OpenAIResponsesGenerator,
)
from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.config import Settings, settings
from app.domain.ports import ProblemFramer
from app.transport.http import create_router
from app.workflows.project_workflow import ProjectWorkflow


def build_problem_framer(
    app_settings: Settings,
) -> tuple[ProblemFramer, OpenAIResponsesGenerator | None]:
    if app_settings.llm_api_key is None:
        return RuleBasedProblemFramer(), None
    generator = OpenAIResponsesGenerator(
        api_key=app_settings.llm_api_key.get_secret_value(),
        model=app_settings.llm_model,
        base_url=app_settings.llm_base_url,
        timeout_seconds=app_settings.llm_timeout_seconds,
    )
    return OpenAIProblemFramer(generator), generator


def create_app(app_settings: Settings = settings) -> FastAPI:
    store = SQLiteProjectStore(app_settings.database_path)
    checkpoint_connection = sqlite3.connect(
        app_settings.checkpoint_database_path,
        check_same_thread=False,
    )
    checkpointer = SqliteSaver(checkpoint_connection)
    framer, model_generator = build_problem_framer(app_settings)
    workflow = ProjectWorkflow(framer, store, checkpointer)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        checkpoint_connection.close()
        if model_generator is not None:
            model_generator.close()

    application = FastAPI(
        title=app_settings.app_name,
        version="0.2.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(create_router(workflow), prefix="/api")
    return application


app = create_app()

