# custom_tool_routes.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from custom_tool_registry import get_custom_tool_registry

custom_tool_router = APIRouter(prefix="/custom-tools", tags=["custom-tools"])


class CustomToolBody(BaseModel):
    name: str
    description: str = ""
    code: str = ""


@custom_tool_router.get("/{username}")
async def list_custom_tools(username: str):
    registry = get_custom_tool_registry(username)
    tools = registry.list_tools()
    return JSONResponse(content={
        "tools": [t.to_dict() for t in tools]
    })


@custom_tool_router.post("/{username}")
async def create_custom_tool(username: str, body: CustomToolBody):
    if not body.name:
        raise HTTPException(status_code=400, detail="Tool name is required")
    registry = get_custom_tool_registry(username)
    if registry.get_tool(body.name):
        raise HTTPException(status_code=409, detail=f"Tool '{body.name}' already exists")
    meta = registry.add_tool(body.name, body.description, body.code)
    return JSONResponse(content={"tool": meta.to_dict()})


@custom_tool_router.put("/{username}/{tool_name}")
async def update_custom_tool(username: str, tool_name: str, body: CustomToolBody):
    registry = get_custom_tool_registry(username)
    meta = registry.update_tool(tool_name, body.description, body.code)
    if not meta:
        raise HTTPException(status_code=404, detail="Tool not found")
    return JSONResponse(content={"tool": meta.to_dict()})


@custom_tool_router.delete("/{username}/{tool_name}")
async def delete_custom_tool(username: str, tool_name: str):
    registry = get_custom_tool_registry(username)
    removed = registry.remove_tool(tool_name)
    if not removed:
        raise HTTPException(status_code=404, detail="Tool not found")
    return JSONResponse(content={"removed": True})
