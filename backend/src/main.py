# server.py

import os
import time
from datetime import datetime
import httpx
from typing import Dict
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

from ServerTee import ServerTee
from FileTransmit import file_router
from custom_tool_routes import custom_tool_router
from workflow_routes import workflow_router
from workflow_session import WorkflowSession
from llm import get_llm

# log name as today's date in YYYY-MM-DD format
today_date = datetime.now().strftime("%Y-%m-%d")
# Create log file path dynamically based on the date
log_file_path = f"log/{today_date}.log"
# Initialize ServerTee with the dynamically generated log file path
tee = ServerTee(log_file_path)
# Print the log file path for reference
print(log_file_path)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.post('/chatbot/{username}')
async def process_string(request: Request, username: str):
    # Get the JSON data from the request
    data = await request.json()
    input_string = data.get('input_string', '')
    llm_model = data.get('llm_model', '')  # Default to 'gemma2' if not provided
    api_key = data.get('api_key', '')

    # Process the string using the dynamically provided llm_model and api_key
    result = await ChatBot(get_llm(llm_model, api_key), input_string)

    # Return the result as JSON
    return JSONResponse(content={'result': result})


# Include file router
app.include_router(file_router)


# Include Custom Tool router
app.include_router(custom_tool_router)

# Include Workflow router
app.include_router(workflow_router)

# ============================================================
# WebSocket workflow execution endpoint (replaces SSE /run)
# ============================================================
workflow_sessions: Dict[str, WorkflowSession] = {}


@app.websocket('/ws/run/{username}')
async def ws_run(websocket: WebSocket, username: str):
    await websocket.accept()
    send_queue: asyncio.Queue = asyncio.Queue(maxsize=0)  # unbounded,配合 put_nowait 防御性编程

    _DONE = object()  # sentinel to signal sender to exit

    def _queue_put(event):
        """Non-blocking write to send_queue. Silently drops on QueueFull
        (events are already persisted in session.output_history)."""
        try:
            send_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass

    async def stream_events(session, gen):
        """Forward session events to send_queue."""
        try:
            async for event in gen:
                if event.get("type") == "waiting_for_input":
                    node_id = event["pending_node_id"]
                    schema = session.get_node_input_schema(node_id)
                    _queue_put({
                        "type": "input_request",
                        "input_hint": schema.get("input_hint", "Please provide input"),
                        "input_type": schema.get("input_type", "text"),
                        "options": schema.get("options", [])
                    })
                    return
                else:
                    _queue_put(event)
            # Execution finished (no interrupt and not cancelled)
            if not session.is_waiting and not session._cancelled:
                _queue_put({"type": "completed"})
                # Delayed cleanup: remove session 5 min after completion
                await asyncio.sleep(300)
                # Identity check: only remove if this is still the current session
                if workflow_sessions.get(username) is session:
                    workflow_sessions.pop(username, None)
        except Exception as e:
            _queue_put({"type": "error", "message": str(e)})
            session.is_running = False
            workflow_sessions.pop(username, None)

    async def sender():
        """Read from send_queue and send to frontend via WebSocket."""
        while True:
            msg = await send_queue.get()
            if msg is _DONE:
                break
            await websocket.send_json(msg)

    async def receiver():
        """Receive messages from frontend and dispatch."""
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")

            if msg_type == "start":
                llm_model = msg.get("llm_model", "")
                api_key = msg.get("api_key", "")
                workflow_name = msg.get("workflow_name", "")
                if not workflow_name:
                    _queue_put({"type": "error", "message": "workflow_name is required"})
                    continue
                thread_id = f"{username}_{int(time.time())}"
                llm = get_llm(llm_model, api_key)

                session = WorkflowSession(username, llm, thread_id, workflow_name)
                workflow_sessions[username] = session
                asyncio.create_task(stream_events(session, session.run()))

            elif msg_type == "input":
                session = workflow_sessions.get(username)
                if not session:
                    _queue_put({"type": "error", "message": "No active session"})
                    continue
                user_input = msg.get("input", "")
                asyncio.create_task(stream_events(session, session.resume(user_input)))

            elif msg_type == "stop":
                session = workflow_sessions.get(username)
                if session:
                    session.cancel()
                    workflow_sessions.pop(username, None)
                _queue_put({"type": "stopped"})

            elif msg_type == "status":
                session = workflow_sessions.get(username)
                if session:
                    status_msg = {
                        "type": "status",
                        "is_running": session.is_running,
                        "is_waiting": session.is_waiting,
                        "output_history": session.output_history
                    }
                    # When waiting for input, include input_request details
                    # so the frontend can restore the input panel state
                    if session.is_waiting:
                        snapshot = session.graph.get_state(session.config)
                        if snapshot.next:
                            schema = session.get_node_input_schema(snapshot.next[0])
                            status_msg["input_hint"] = schema.get("input_hint", "Please provide input")
                            status_msg["input_type"] = schema.get("input_type", "text")
                            status_msg["input_options"] = schema.get("options", [])
                    _queue_put(status_msg)
                else:
                    _queue_put({
                        "type": "status",
                        "is_running": False,
                        "is_waiting": False,
                        "output_history": []
                    })

    try:
        await asyncio.gather(sender(), receiver())
    except WebSocketDisconnect:
        # Frontend closed the window; session keeps running in background
        pass
    finally:
        send_queue.put_nowait(_DONE)

# Catch-all route for unmatched GET requests
@app.api_route("/{anypath:path}", methods=["GET"])
async def catch_all(request: Request, anypath: str):
    print(f"Unmatched GET request: {anypath}")
    return JSONResponse(content={"message": f"Route {anypath} not found"}, status_code=404)


# Run the app using Uvicorn
if __name__ == "__main__":
    import uvicorn

    backend_port = int(os.environ.get("BACKEND_PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=backend_port, reload=True)