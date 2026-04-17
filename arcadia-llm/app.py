import os
import logging
import shutil
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingest import run_ingest, query_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── LLM config ────────────────────────────────────────────────────────────────
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY")          # required — passed at docker run
LLM_MODEL   = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ── RAG config ────────────────────────────────────────────────────────────────
DOCS_DIR    = os.getenv("DOCS_DIR",    "/app/docs")
CHROMA_DIR  = os.getenv("CHROMA_DIR",  "/app/chromadb")
CHUNK_SIZE      = int(os.getenv("CHUNK_SIZE",      "500"))
CHUNK_OVERLAP   = int(os.getenv("CHUNK_OVERLAP",   "50"))
VECTOR_TOP_K    = int(os.getenv("VECTOR_TOP_K",    "4"))

SYSTEM_PROMPT = (
    "You are Aria, a friendly and professional customer support assistant for Arcadia Finance. "
    "You help customers with account inquiries, stock trading, portfolio management, money transfers, "
    "credit card applications, and general financial planning questions. "
    "Keep responses concise and helpful. "
    "For sensitive account actions such as withdrawals or password changes, "
    "always direct the customer to log in at the portal or call our support line at 888-123-2323. "
    "Use the CONTEXT section below — if it contains relevant information, prioritise it in your answer."
)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Arcadia LLM")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []


# ── Chat ──────────────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(request: ChatRequest):
    if not LLM_API_KEY:
        raise HTTPException(status_code=500, detail="LLM_API_KEY is not set")

    # 1. Retrieve relevant context from ChromaDB
    context_chunks = query_context(
        query=request.message,
        chroma_dir=CHROMA_DIR,
        top_k=VECTOR_TOP_K,
    )
    context_text = "\n\n".join(context_chunks) if context_chunks else ""

    # 2. Build system message with injected context
    system_content = SYSTEM_PROMPT
    if context_text:
        system_content += f"\n\nCONTEXT:\n{context_text}"

    # 3. Assemble messages: system + history (last 10) + new user message
    messages = [{"role": "system", "content": system_content}]
    for msg in request.history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                LLM_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"LLM request failed: {e}")
            raise HTTPException(status_code=502, detail="LLM service unavailable")

    reply = resp.json()["choices"][0]["message"]["content"].strip()
    return {"response": reply}


# ── File upload ───────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    dest = Path(DOCS_DIR) / file.filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    logger.info(f"Uploaded: {dest}")
    return {"filename": file.filename, "status": "uploaded"}


# ── Ingest ────────────────────────────────────────────────────────────────────
@app.post("/ingest")
async def ingest(background_tasks: BackgroundTasks):
    background_tasks.add_task(
        run_ingest,
        docs_dir=DOCS_DIR,
        chroma_dir=CHROMA_DIR,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return {"status": "ingestion started"}


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_model": LLM_MODEL,
        "docs_dir": DOCS_DIR,
        "chroma_dir": CHROMA_DIR,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "vector_top_k": VECTOR_TOP_K,
    }
