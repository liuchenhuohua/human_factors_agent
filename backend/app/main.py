import os
import sqlite3
from contextlib import asynccontextmanager

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver

from app.adapters.openai_problem_framer import OpenAIProblemFramer
from app.adapters.openai_responses import OpenAIResponsesGenerator
from app.adapters.crossref_search import CrossrefLiteratureSearch
from app.adapters.evidence_planner import OpenAIEvidencePlanner, RuleBasedEvidencePlanner
from app.adapters.evidence_synthesis import (
    OpenAIEvidenceAppraiser,
    OpenAIEvidenceSynthesizer,
    RuleBasedEvidenceAppraiser,
    RuleBasedEvidenceSynthesizer,
)
from app.adapters.experiment_designer import (
    OpenAIExperimentDesigner,
    RuleBasedExperimentDesigner,
)
from app.adapters.data_contract_builder import (
    CsvDataTemplateRenderer,
    RuleBasedDataContractBuilder,
)
from app.adapters.csv_dataset_validator import CsvDatasetValidator
from app.adapters.evidence_extractor import (
    OpenAIEvidenceExtractor,
    RuleBasedEvidenceExtractor,
)
from app.adapters.local_document_storage import LocalDocumentStorage
from app.adapters.local_dataset_storage import LocalDatasetStorage
from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.pypdf_parser import PypdfTextExtractor
from app.adapters.power_calculator import StatsmodelsPowerCalculator
from app.adapters.sqlite_evidence_store import SQLiteEvidenceStore
from app.adapters.sqlite_dataset_store import SQLiteDatasetStore
from app.adapters.sqlite_experiment_store import SQLiteExperimentStore
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.adapters.sqlite_preparation_store import SQLitePreparationStore
from app.config import Settings, settings
from app.domain.ports import ProblemFramer
from app.transport.evidence_http import create_evidence_router
from app.transport.dataset_http import create_dataset_router
from app.transport.experiment_http import create_experiment_router
from app.transport.preparation_http import create_preparation_router
from app.transport.http import create_router
from app.workflows.evidence_workflow import EvidenceWorkflow
from app.workflows.dataset_workflow import DatasetWorkflow
from app.workflows.experiment_workflow import ExperimentWorkflow
from app.workflows.preparation_workflow import PreparationWorkflow
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
    evidence_store = SQLiteEvidenceStore(app_settings.database_path)
    experiment_store = SQLiteExperimentStore(app_settings.database_path)
    preparation_store = SQLitePreparationStore(app_settings.database_path)
    dataset_store = SQLiteDatasetStore(app_settings.database_path)
    checkpoint_connection = sqlite3.connect(
        app_settings.checkpoint_database_path,
        check_same_thread=False,
    )
    checkpointer = SqliteSaver(checkpoint_connection)
    framer, model_generator = build_problem_framer(app_settings)
    workflow = ProjectWorkflow(framer, store, checkpointer)
    evidence_planner = (
        OpenAIEvidencePlanner(model_generator)
        if model_generator is not None
        else RuleBasedEvidencePlanner()
    )
    literature_search = CrossrefLiteratureSearch(
        base_url=app_settings.crossref_base_url,
        timeout_seconds=app_settings.crossref_timeout_seconds,
        mailto=app_settings.crossref_mailto,
    )
    evidence_extractor = (
        OpenAIEvidenceExtractor(model_generator)
        if model_generator is not None
        else RuleBasedEvidenceExtractor()
    )
    evidence_appraiser = (
        OpenAIEvidenceAppraiser(model_generator)
        if model_generator is not None
        else RuleBasedEvidenceAppraiser()
    )
    evidence_synthesizer = (
        OpenAIEvidenceSynthesizer(model_generator)
        if model_generator is not None
        else RuleBasedEvidenceSynthesizer()
    )
    evidence_workflow = EvidenceWorkflow(
        evidence_planner,
        literature_search,
        store,
        evidence_store,
        LocalDocumentStorage(app_settings.document_storage_path),
        PypdfTextExtractor(app_settings.max_pdf_pages),
        evidence_extractor,
        evidence_appraiser,
        evidence_synthesizer,
        checkpointer=checkpointer,
        max_upload_bytes=app_settings.max_pdf_upload_mb * 1024 * 1024,
    )
    experiment_designer = (
        OpenAIExperimentDesigner(model_generator)
        if model_generator is not None
        else RuleBasedExperimentDesigner()
    )
    experiment_workflow = ExperimentWorkflow(
        experiment_designer,
        store,
        evidence_store,
        experiment_store,
    )
    preparation_workflow = PreparationWorkflow(
        StatsmodelsPowerCalculator(),
        RuleBasedDataContractBuilder(),
        CsvDataTemplateRenderer(),
        experiment_store,
        preparation_store,
    )
    dataset_workflow = DatasetWorkflow(
        CsvDatasetValidator(),
        LocalDatasetStorage(app_settings.dataset_storage_path),
        dataset_store,
        preparation_workflow,
        max_upload_bytes=app_settings.max_csv_upload_mb * 1024 * 1024,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        checkpoint_connection.close()
        if model_generator is not None:
            model_generator.close()
        literature_search.close()

    application = FastAPI(
        title=app_settings.app_name,
        version="0.8.0",
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
    application.include_router(
        create_evidence_router(evidence_workflow), prefix="/api"
    )
    application.include_router(
        create_experiment_router(experiment_workflow), prefix="/api"
    )
    application.include_router(
        create_preparation_router(preparation_workflow), prefix="/api"
    )
    application.include_router(create_dataset_router(dataset_workflow), prefix="/api")
    return application


app = create_app()

