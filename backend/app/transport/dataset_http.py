from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from app.domain.dataset import DatasetRegistry, DatasetReviewRequest
from app.domain.dataset_ports import DatasetValidationError
from app.workflows.dataset_workflow import DatasetWorkflow


def create_dataset_router(workflow: DatasetWorkflow) -> APIRouter:
    router = APIRouter()

    @router.get("/projects/{project_id}/datasets", response_model=DatasetRegistry)
    def get_datasets(project_id: UUID) -> DatasetRegistry:
        registry = workflow.get(project_id)
        if registry is None:
            raise HTTPException(status_code=404, detail="Datasets not found")
        return registry

    @router.post("/projects/{project_id}/datasets", response_model=DatasetRegistry)
    async def upload_dataset(
        project_id: UUID,
        file: Annotated[UploadFile, File(description="UTF-8 CSV dataset")],
    ) -> DatasetRegistry:
        content = await file.read(workflow.max_upload_bytes + 1)
        await file.close()
        try:
            return workflow.upload(
                project_id=project_id,
                filename=file.filename or "",
                content_type=file.content_type,
                content=content,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except DatasetValidationError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.put(
        "/projects/{project_id}/datasets/{dataset_id}",
        response_model=DatasetRegistry,
    )
    def review_dataset(
        project_id: UUID,
        dataset_id: UUID,
        request: DatasetReviewRequest,
    ) -> DatasetRegistry:
        try:
            return workflow.review(project_id, dataset_id, request)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.get("/projects/{project_id}/datasets/{dataset_id}/source.csv")
    def download_dataset(project_id: UUID, dataset_id: UUID) -> Response:
        try:
            dataset, content = workflow.download(project_id, dataset_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="dataset-v{dataset.version}-{dataset.id}.csv"'
                ),
                "X-Content-SHA256": dataset.sha256,
            },
        )

    return router
