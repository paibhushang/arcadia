import os
import logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMMA_URL = os.getenv("GEMMA_URL", "http://ollama:11434/v1/chat/completions")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4:4b")

SYSTEM_PROMPT = (
    "You are Aria, a friendly and professional customer support assistant for Arcadia Finance. "
    "You help customers with account inquiries, stock trading, portfolio management, money transfers, "
    "credit card applications, and general financial planning questions. "
    "Keep responses concise and helpful. "
    "For sensitive account actions such as withdrawals or password changes, "
    "always direct the customer to log in at the portal or call our support line at 888-123-2323."
)

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
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in request.history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    payload = {
        "model": GEMMA_MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(GEMMA_URL, json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Gemma request failed: {e}")
            raise HTTPException(status_code=502, detail="Model service unavailable")

    data = resp.json()
    reply = data["choices"][0]["message"]["content"].strip()
    return {"response": reply}


@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(GEMMA_URL.replace("/v1/chat/completions", "/"))
            model_status = "ok" if r.is_success else "unreachable"
        except httpx.HTTPError:
            model_status = "unreachable"
    return {"status": "ok", "model_service": model_status}
