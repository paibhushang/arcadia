import os
import logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM_URL = os.getenv("LLM_URL", "http://arcadia-llm:8001/chat")

app = FastAPI(title="Arcadia Finance Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []


@app.post("/chat")
async def chat(request: ChatRequest):
    payload = {
        "message": request.message,
        "history": [msg.model_dump() for msg in request.history],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(LLM_URL, json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"arcadia-llm request failed: {e}")
            raise HTTPException(status_code=502, detail="LLM service unavailable")

    return resp.json()


@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(LLM_URL.replace("/chat", "/health"))
            llm_status = "ok" if r.is_success else "unreachable"
        except httpx.HTTPError:
            llm_status = "unreachable"
    return {"status": "ok", "arcadia_llm": llm_status}
