from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from app.domain.preparation import (
    DataContractReviewRequest,
    PowerAnalysisRequest,
    PowerAnalysisReviewRequest,
    StudyPreparation,
)
from app.domain.preparation_ports import PowerCalculationError
from app.workflows.preparation_workflow import PreparationWorkflow


def create_preparation_router(workflow: PreparationWorkflow) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/projects/{project_id}/study-preparation",
        response_model=StudyPreparation,
    )
    def get_preparation(project_id: UUID) -> StudyPreparation:
        preparation = workflow.get(project_id)
        if preparation is None:
            raise HTTPException(status_code=404, detail="Study preparation not found")
        return preparation

    @router.post(
        "/projects/{project_id}/study-preparation/power-analysis",
        response_model=StudyPreparation,
    )
    def calculate_power(
        project_id: UUID,
        request: PowerAnalysisRequest,
    ) -> StudyPreparation:
        try:
            return workflow.calculate_power(project_id, request)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except PowerCalculationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.put(
        "/projects/{project_id}/study-preparation/power-analysis",
        response_model=StudyPreparation,
    )
    def review_power(
        project_id: UUID,
        request: PowerAnalysisReviewRequest,
    ) -> StudyPreparation:
        try:
            return workflow.review_power(project_id, request)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post(
        "/projects/{project_id}/study-preparation/data-contract",
        response_model=StudyPreparation,
    )
    def generate_contract(project_id: UUID) -> StudyPreparation:
        try:
            return workflow.generate_data_contract(project_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.put(
        "/projects/{project_id}/study-preparation/data-contract",
        response_model=StudyPreparation,
    )
    def review_contract(
        project_id: UUID,
        request: DataContractReviewRequest,
    ) -> StudyPreparation:
        try:
            return workflow.review_data_contract(project_id, request)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.get("/projects/{project_id}/study-preparation/template.csv")
    def download_template(project_id: UUID) -> Response:
        try:
            content = workflow.render_csv_template(project_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="human-factors-{project_id}-template.csv"'
                )
            },
        )

    return router
