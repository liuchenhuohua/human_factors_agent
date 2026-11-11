from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.domain.evidence import (
    EvidenceReview,
    ScreeningRequest,
    SearchPlanContent,
)
from app.domain.evidence_ports import EvidencePlanningError, LiteratureSearchError
from app.workflows.evidence_workflow import EvidenceWorkflow


def create_evidence_router(workflow: EvidenceWorkflow) -> APIRouter:
    router = APIRouter()

    @router.post("/projects/{project_id}/evidence", response_model=EvidenceReview)
    def start_evidence_review(project_id: UUID) -> EvidenceReview:
        try:
            return workflow.start(project_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except EvidencePlanningError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.get("/projects/{project_id}/evidence", response_model=EvidenceReview)
    def get_evidence_review(project_id: UUID) -> EvidenceReview:
        review = workflow.get(project_id)
        if review is None:
            raise HTTPException(status_code=404, detail="Evidence review not found")
        return review

    @router.post(
        "/projects/{project_id}/evidence/search-plan/approve",
        response_model=EvidenceReview,
    )
    def approve_search_plan(
        project_id: UUID, content: SearchPlanContent
    ) -> EvidenceReview:
        try:
            return workflow.approve_search_plan(project_id, content)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except LiteratureSearchError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.post(
        "/projects/{project_id}/evidence/candidates/{candidate_id}/screen",
        response_model=EvidenceReview,
    )
    def screen_candidate(
        project_id: UUID,
        candidate_id: UUID,
        request: ScreeningRequest,
    ) -> EvidenceReview:
        try:
            return workflow.screen_candidate(project_id, candidate_id, request)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return router
