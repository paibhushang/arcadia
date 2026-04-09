import os
import logging
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_ID = os.getenv("MODEL_ID", "google/gemma-4-E4B")
HF_TOKEN = os.getenv("HF_TOKEN", None)

SYSTEM_PROMPT = (
    "You are Aria, a friendly and professional customer support assistant for Arcadia Finance. "
    "You help customers with account inquiries, stock trading, portfolio management, money transfers, "
    "credit card applications, and general financial planning questions. "
    "Keep responses concise and helpful. "
    "For sensitive account actions such as withdrawals or password changes, "
    "always direct the customer to log in at the portal or call our support line at 888-123-2323."
)

tokenizer = None
model = None
executor = ThreadPoolExecutor(max_workers=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tokenizer, model
    logger.info(f"Loading model: {MODEL_ID}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        token=HF_TOKEN,
    )
    model.eval()
    logger.info("Model loaded and ready")
    yield
    executor.shutdown(wait=False)


app = FastAPI(title="Arcadia Finance Chatbot", lifespan=lifespan)

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


def _generate(messages: list[dict]) -> str:
    input_ids = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True,
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            input_ids,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    return tokenizer.decode(
        output_ids[0][input_ids.shape[-1]:],
        skip_special_tokens=True,
    ).strip()


@app.post("/chat")
async def chat(request: ChatRequest):
    import asyncio

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in request.history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(executor, _generate, messages)
    return {"response": response}


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_ID}
