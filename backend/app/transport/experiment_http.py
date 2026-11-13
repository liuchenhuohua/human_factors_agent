from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.domain.experiment import ExperimentPlan, ExperimentPlanReviewRequest
from app.domain.experiment_ports import ExperimentDesignError
from app.workflows.experiment_workflow import ExperimentWorkflow


def create_experiment_router(workflow: ExperimentWorkflow) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/projects/{project_id}/experiment-plan",
        response_model=ExperimentPlan,
    )
    def start_experiment_plan(project_id: UUID) -> ExperimentPlan:
        try:
            return workflow.start(project_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ExperimentDesignError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    @router.get(
        "/projects/{project_id}/experiment-plan",
        response_model=ExperimentPlan,
    )
    def get_experiment_plan(project_id: UUID) -> ExperimentPlan:
        plan = workflow.get(project_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Experiment plan not found")
        return plan

    @router.put(
        "/projects/{project_id}/experiment-plan",
        response_model=ExperimentPlan,
    )
    def review_experiment_plan(
        project_id: UUID,
        request: ExperimentPlanReviewRequest,
    ) -> ExperimentPlan:
        try:
            return workflow.review(project_id, request)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    return router
