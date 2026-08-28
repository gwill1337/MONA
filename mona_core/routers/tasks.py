from mona_core.config import celery_client
from mona_core.schemas import TaskStatusOut
from mona_core.security import user_router


@user_router.get("/task-status/{task_id}", response_model=TaskStatusOut)
def get_task_status(task_id: str) -> TaskStatusOut:
    result = celery_client.AsyncResult(task_id)

    raw = None
    if result.ready():
        try:
            raw = result.result
            if isinstance(raw, Exception):
                raw = {"error": str(raw)}
        except Exception:
            raw = None

    return TaskStatusOut(task_id=task_id, state=result.state, result=raw)
