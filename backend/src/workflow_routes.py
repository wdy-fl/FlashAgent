# workflow_routes.py

import os
import re
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

workflow_router = APIRouter()

# Valid workflow name: alphanumeric, underscores, hyphens only
_WORKFLOW_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class WorkflowSaveRequest(BaseModel):
    name: str
    nodes: list


def _validate_name(name: str):
    """Validate workflow name to prevent path traversal attacks."""
    if not name:
        raise HTTPException(status_code=400, detail="Workflow name cannot be empty")
    if not _WORKFLOW_NAME_PATTERN.match(name):
        raise HTTPException(
            status_code=400,
            detail="Workflow name must contain only letters, numbers, underscores, and hyphens"
        )


def _workflows_dir(username: str) -> str:
    d = os.path.join("workspace", username, "workflows")
    os.makedirs(d, exist_ok=True)
    return d


def _workflow_path(username: str, name: str) -> str:
    return os.path.join(_workflows_dir(username), f"{name}.json")


@workflow_router.get("/workflows/{username}")
async def list_workflows(username: str):
    d = _workflows_dir(username)
    names = [os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".json")]
    return {"workflows": sorted(names)}


@workflow_router.get("/workflows/{username}/{name}")
async def get_workflow(username: str, name: str):
    _validate_name(name)
    path = _workflow_path(username, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Workflow not found")
    with open(path, "r") as f:
        return json.load(f)


@workflow_router.post("/workflows/{username}")
async def save_workflow(
    username: str,
    body: WorkflowSaveRequest,
    overwrite: bool = Query(False)
):
    _validate_name(body.name)
    path = _workflow_path(username, body.name)
    if os.path.exists(path) and not overwrite:
        raise HTTPException(status_code=409, detail="Workflow name already exists")
    data = {
        "name": body.name,
        "nodes": body.nodes,
        "updated_at": datetime.now().isoformat()
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return {"message": "saved"}


@workflow_router.delete("/workflows/{username}/{name}")
async def delete_workflow(username: str, name: str):
    _validate_name(name)
    path = _workflow_path(username, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Workflow not found")
    os.remove(path)
    return {"message": "deleted"}
