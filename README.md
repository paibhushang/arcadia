# Arcadia Finance

A demo microservices banking application with an AI-powered support chat backed by a RAG (Retrieval-Augmented Generation) pipeline.

![Architecture](Micro%20Services%20architecture.png)

---

## Architecture

| Service | Role | Internal hostname | Port |
|---------|------|-------------------|------|
| **Nginx** | API gateway / reverse proxy | `nginx` | 80 (public) |
| **MainApp** | Public website + trading dashboard | `mainapp` | 80 |
| **Backend** | Data persistence (accounts, stocks, transfers) | `backend` | 80 |
| **App2** | REST API for money transfers | `app2` | 80 |
| **App3** | Credit card requests + logging | `app3` | 80 |
| **arcadia-llm** | RAG service — ChromaDB + embeddings + LLM proxy | `arcadia-llm` | 8001 |
| **Chatbot** | Thin chat API + browser widget | `chatbot` | 8000 |

All services communicate over an internal Docker network. Nginx is the only publicly exposed port (80).

### Chat request flow

```
Browser → Nginx → chatbot:8000 → arcadia-llm:8001
                                   ├── query ChromaDB (sentence-transformers)
                                   └── POST to external LLM API (OpenAI-compatible)
```

---

## Prerequisites

Install Docker Engine and Docker Compose on Ubuntu:

```bash
# Remove any old Docker packages
sudo apt-get remove -y docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key and repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Allow running Docker without sudo (log out and back in after this)
sudo usermod -aG docker $USER
```

Verify the install:

```bash
docker --version
docker compose version
```

---

## Clone the repository

```bash
git clone https://github.com/paibhushang/arcadia.git
cd arcadia
```

---

## Configuration

`arcadia-llm` requires an LLM API key. Set it as an environment variable before starting:

```bash
export LLM_API_KEY=sk-...
```

Optional overrides (defaults shown):

```bash
export LLM_API_URL=https://api.openai.com/v1/chat/completions
export LLM_MODEL=gpt-4o-mini
export CHUNK_SIZE=500       # characters per document chunk
export CHUNK_OVERLAP=50     # overlap between consecutive chunks
export VECTOR_TOP_K=4       # number of ChromaDB results injected into each prompt
```

---

## Build and run

### Option 1 — Docker Compose (recommended)

```bash
LLM_API_KEY=sk-... docker compose up --build -d
```

Check all containers are running:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f arcadia-llm
docker compose logs -f chatbot
```

Stop everything:

```bash
docker compose down
```

---

### Option 2 — Docker run (manual)

Build all images and create the shared network:

```bash
docker network create internal

docker build -t arcadia_mainapp   ./main/MainApp
docker build -t arcadia_backend   ./backend
docker build -t arcadia_app2      ./app2
docker build -t arcadia_app3      ./app3
docker build -t arcadia_llm       ./arcadia-llm
docker build -t arcadia_chatbot   ./chatbot
docker build -t arcadia_nginx     ./Nginx
```

Start each service:

```bash
# Backend (data layer)
docker run -dit -h backend --name=backend --net=internal \
  -v $(pwd)/backend/files:/var/www/html/files \
  arcadia_backend

# App2 (money transfer API)
docker run -dit -h app2 --name=app2 --net=internal \
  -v $(pwd)/app2/api:/var/www/html/api \
  arcadia_app2

# App3 (credit card and logging)
docker run -dit -h app3 --name=app3 --net=internal \
  -v $(pwd)/app3/app3:/var/www/html/app3 \
  arcadia_app3

# MainApp (website and dashboard)
docker run -dit -h mainapp --name=mainapp --net=internal \
  -v $(pwd)/main/MainApp:/var/www/html \
  arcadia_mainapp

# arcadia-llm (RAG + LLM service)
docker run -dit -h arcadia-llm --name=arcadia-llm --net=internal \
  -e LLM_API_KEY=sk-... \
  -e LLM_MODEL=gpt-4o-mini \
  -e CHUNK_SIZE=500 \
  -e CHUNK_OVERLAP=50 \
  -e VECTOR_TOP_K=4 \
  -v $(pwd)/arcadia-llm/docs:/app/docs \
  -v $(pwd)/arcadia-llm/chromadb:/app/chromadb \
  arcadia_llm

# Chatbot (thin proxy + browser widget)
docker run -dit -h chatbot --name=chatbot --net=internal \
  -e LLM_URL=http://arcadia-llm:8001/chat \
  arcadia_chatbot

# Nginx API gateway (publicly exposed on port 80)
docker run -dit -h nginx --name=nginx --net=internal \
  -p 80:80 \
  -v $(pwd)/Nginx/default.conf:/etc/nginx/conf.d/default.conf \
  arcadia_nginx
```

---

## Access the app

| URL | Description |
|-----|-------------|
| `http://localhost` | Public homepage |
| `http://localhost/trading/login.php` | Trading dashboard login |
| `http://localhost/api` | Money transfer REST API |
| `http://localhost/files` | Data files service |
| `http://localhost/app3` | Credit card / App3 |
| `http://localhost/arcadia-llm/admin` | Knowledge base admin UI |
| `http://localhost/arcadia-llm/health` | arcadia-llm health + config |
| `http://localhost/chatbot/health` | Chatbot health check |

**Login credentials for the trading dashboard:**

```
Username: admin
Password: iloveblue
```

The support chat widget (Aria) appears as a floating button in the bottom-right corner of every page.

---

## Knowledge base — uploading documents and ingesting context

`arcadia-llm` uses a local ChromaDB vector store to provide Aria with relevant context when answering questions. You can add documents via the admin UI or the API directly.

### Admin UI (recommended)

Open `http://localhost/arcadia-llm/admin` in a browser.

1. **Upload documents** — drag and drop or browse for files (`.txt`, `.md`, `.pdf`, `.csv`, `.json`). Files are saved to `arcadia-llm/docs/`.
2. **Run Ingestion** — click the button to chunk the documents, generate embeddings (via `sentence-transformers/all-MiniLM-L6-v2`), and store them in ChromaDB at `arcadia-llm/chromadb/`.
3. The **Documents in Knowledge Base** table shows all files currently in the docs directory.

### API

Upload a file:

```bash
curl -X POST http://localhost/arcadia-llm/upload \
  -F "file=@/path/to/document.pdf"
```

Trigger ingestion (runs in background):

```bash
curl -X POST http://localhost/arcadia-llm/ingest
```

Check ingestion progress in the logs:

```bash
docker compose logs -f arcadia-llm
```

---

## arcadia-llm environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | _(required)_ | API key for the LLM provider |
| `LLM_API_URL` | OpenAI endpoint | Any OpenAI-compatible URL |
| `LLM_MODEL` | `gpt-4o-mini` | Model name passed to the API |
| `CHUNK_SIZE` | `500` | Characters per document chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between consecutive chunks |
| `VECTOR_TOP_K` | `4` | Number of ChromaDB results injected into each prompt |
| `DOCS_DIR` | `/app/docs` | Directory where uploaded documents are stored |
| `CHROMA_DIR` | `/app/chromadb` | Directory where ChromaDB persists data |

---

## Project structure

```
arcadia-finance/
├── main/MainApp/       # Public website + trading dashboard (PHP/Apache)
├── backend/files/      # JSON data store (accounts, stocks, transfers)
├── app2/api/           # Money transfer REST API (PHP/Apache)
├── app3/app3/          # Credit card requests + logging (PHP/Apache)
├── arcadia-llm/        # RAG service (FastAPI)
│   ├── app.py          # API endpoints: /chat /upload /ingest /docs-list /admin /health
│   ├── ingest.py       # Document chunking, embedding, ChromaDB upsert and query
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docs/           # Uploaded source documents (mounted volume)
│   ├── chromadb/       # Persisted ChromaDB vector store (mounted volume)
│   └── static/
│       └── admin.html  # Knowledge base admin web UI
├── chatbot/            # Thin chat proxy + browser widget (FastAPI)
│   └── static/         # Chat widget JS and CSS
├── Nginx/              # API gateway config and Dockerfile
│   └── default.conf
└── docker-compose.yml
```

---

## AWS S3 configuration (optional)

The contact form can optionally upload submissions to an S3 bucket. Configure credentials at `http://localhost/config.php` after logging in, or edit `main/MainApp/trading/aws.json` directly.

The file ships with placeholder values. Replace `REPLACE_WITH_YOUR_IAM_KEY` and `REPLACE_WITH_YOUR_IAM_SECRET` with real credentials if you want S3 uploads to work.
