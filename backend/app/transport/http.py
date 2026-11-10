from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.domain.project import Project, ProjectIntake, ProjectStage
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
        return workflow.start(intake)

    @router.get("/projects/{project_id}", response_model=Project)
    def get_project(project_id: UUID) -> Project:
        project = workflow.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @router.post("/projects/{project_id}/problem-frame/approve", response_model=Project)
    def approve_problem_frame(project_id: UUID) -> Project:
        project = workflow.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.stage is not ProjectStage.PROBLEM_FRAME_REVIEW:
            raise HTTPException(status_code=409, detail="Problem frame is not awaiting review")
        try:
            return workflow.approve_problem_frame(project_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return router

