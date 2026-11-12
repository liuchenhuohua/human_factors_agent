from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.domain.evidence import (
    EvidenceItemReviewRequest,
    EvidenceReview,
    ScreeningRequest,
    SearchPlanContent,
)
from app.domain.evidence_ports import (
    DocumentParsingError,
    DocumentValidationError,
    EvidenceExtractionError,
    EvidencePlanningError,
    LiteratureSearchError,
)
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
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post(
        "/projects/{project_id}/evidence/candidates/{candidate_id}/document",
        response_model=EvidenceReview,
    )
    async def upload_candidate_document(
        project_id: UUID,
        candidate_id: UUID,
        file: Annotated[UploadFile, File(description="Selectable-text research PDF")],
    ) -> EvidenceReview:
        content = await file.read(workflow.max_upload_bytes + 1)
        await file.close()
        try:
            return workflow.upload_pdf(
                project_id=project_id,
                candidate_id=candidate_id,
                filename=file.filename or "",
                content_type=file.content_type,
                content=content,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (DocumentValidationError, DocumentParsingError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except EvidenceExtractionError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.put(
        "/projects/{project_id}/evidence/evidence-items/{item_id}",
        response_model=EvidenceReview,
    )
    def review_evidence_item(
        project_id: UUID,
        item_id: UUID,
        request: EvidenceItemReviewRequest,
    ) -> EvidenceReview:
        try:
            return workflow.review_evidence_item(project_id, item_id, request)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (DocumentValidationError, DocumentParsingError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return router
