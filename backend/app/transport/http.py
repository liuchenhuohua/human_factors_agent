from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.domain.ports import ProblemFramingError
from app.domain.project import (
    ClarificationSubmission,
    ProblemFrameContent,
    Project,
    ProjectIntake,
    ProjectStage,
    RevisionRequest,
)
from app.workflows.project_workflow import ProjectWorkflow


def create_router(workflow: ProjectWorkflow) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/projects", response_model=list[Project])
    def list_projects() -> list[Project]:
        return workflow.list()

    @router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
    def create_project(intake: ProjectIntake) -> Project:
        try:
            return workflow.start(intake)
        except ProblemFramingError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.get("/projects/{project_id}", response_model=Project)
    def get_project(project_id: UUID) -> Project:
        return require_project(workflow, project_id)

    @router.post("/projects/{project_id}/clarifications", response_model=Project)
    def submit_clarifications(
        project_id: UUID, submission: ClarificationSubmission
    ) -> Project:
        project = require_project(workflow, project_id)
        require_stage(project, ProjectStage.CLARIFICATION_REQUIRED)
        try:
            return workflow.submit_clarifications(project_id, submission.answers)
        except ProblemFramingError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.put("/projects/{project_id}/problem-frame", response_model=Project)
    def edit_problem_frame(
        project_id: UUID, content: ProblemFrameContent
    ) -> Project:
        project = require_project(workflow, project_id)
        require_stage(project, ProjectStage.PROBLEM_FRAME_REVIEW)
        try:
            return workflow.edit_problem_frame(project_id, content)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post("/projects/{project_id}/problem-frame/revise", response_model=Project)
    def revise_problem_frame(project_id: UUID, request: RevisionRequest) -> Project:
        project = require_project(workflow, project_id)
        require_stage(project, ProjectStage.PROBLEM_FRAME_REVIEW)
        try:
            return workflow.request_problem_frame_revision(project_id, request.feedback)
        except ProblemFramingError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.post("/projects/{project_id}/problem-frame/approve", response_model=Project)
    def approve_problem_frame(project_id: UUID) -> Project:
        project = require_project(workflow, project_id)
        require_stage(project, ProjectStage.PROBLEM_FRAME_REVIEW)
        return workflow.approve_problem_frame(project_id)

    return router


def require_project(workflow: ProjectWorkflow, project_id: UUID) -> Project:
    project = workflow.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_stage(project: Project, expected: ProjectStage) -> None:
    if project.stage is not expected:
        raise HTTPException(
            status_code=409,
            detail=f"Project is in stage '{project.stage}', expected '{expected}'",
        )

