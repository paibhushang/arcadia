# Arcadia Finance

A demo microservices banking application with an AI-powered support chat.

![Architecture](Micro%20Services%20architecture.png)

---

## Architecture

| Service | Role | Internal hostname |
|---------|------|-------------------|
| **Nginx** | API gateway / reverse proxy | `nginx` |
| **MainApp** | Public website + trading dashboard | `mainapp` |
| **Backend** | Data persistence (accounts, stocks, transfers) | `backend` |
| **App2** | REST API for money transfers | `app2` |
| **App3** | Credit card requests + logging | `app3` |
| **Gemma4** | Local LLM model server (`ai/gemma4`) | `gemma4` |
| **Chatbot** | Support chat API + widget | `chatbot` |

All services communicate over an internal Docker network. Nginx is the only publicly exposed port (80).

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

## Build and run

### Option 1 — Docker Compose (recommended)

Build the images and start all services:

```bash
docker compose up --build -d
```

This builds the **MainApp**, **Backend**, **App2**, **App3**, and **Chatbot** images locally, pulls `ai/gemma4`, and starts everything.

Check that all containers are running:

```bash
docker compose ps
```

View logs for a specific service:

```bash
docker compose logs -f chatbot
docker compose logs -f gemma4
```

Stop everything:

```bash
docker compose down
```

---

### Option 2 — Docker run (manual)

First create the shared network and build the images:

```bash
docker network create internal

docker build -t arcadia_mainapp  ./main/MainApp
docker build -t arcadia_backend  ./backend
docker build -t arcadia_app2     ./app2
docker build -t arcadia_app3     ./app3
docker build -t arcadia_chatbot  ./chatbot
docker build -t arcadia_nginx    ./Nginx
```

Then start each service:

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

# Gemma4 model server
docker run -dit -h gemma4 --name=gemma4 --net=internal \
  ai/gemma4

# Chatbot API
docker run -dit -h chatbot --name=chatbot --net=internal \
  -e GEMMA_URL=http://gemma4:8080/v1/chat/completions \
  arcadia_chatbot

# Nginx API gateway (publicly exposed on port 80)
docker run -dit -h nginx --name=nginx --net=internal \
  -p 80:80 \
  -v $(pwd)/Nginx/default.conf:/etc/nginx/conf.d/default.conf \
  arcadia_nginx
```

---

## Access the app

Once all services are running, open a browser:

| URL | Description |
|-----|-------------|
| `http://localhost` | Public homepage |
| `http://localhost/trading/login.php` | Trading dashboard login |
| `http://localhost/api` | Money transfer REST API |
| `http://localhost/files` | Data files service |
| `http://localhost/app3` | Credit card / App3 |
| `http://localhost/chatbot/health` | Chatbot health check |

**Login credentials for the trading dashboard:**

```
Username: admin
Password: iloveblue
```

The support chat widget (Aria) appears as a floating button in the bottom-right corner of every page.

---

## GPU acceleration for Gemma4 (optional)

For faster chat responses, enable GPU passthrough to the `gemma4` container.

Install the NVIDIA Container Toolkit:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Then uncomment the `deploy` block in `docker-compose.yml` under the `gemma4` service:

```yaml
  gemma4:
    image: ai/gemma4
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Restart the gemma4 service:

```bash
docker compose up -d gemma4
```

---

## Project structure

```
arcadia-finance/
├── main/MainApp/       # Public website + trading dashboard (PHP/Apache)
├── backend/files/      # JSON data store (accounts, stocks, transfers)
├── app2/api/           # Money transfer REST API (PHP/Apache)
├── app3/app3/          # Credit card requests + logging (PHP/Apache)
├── chatbot/            # AI support chat service (FastAPI + httpx)
│   └── static/         # Chat widget JS and CSS served to the browser
├── Nginx/              # API gateway config and Dockerfile
│   └── default.conf
└── docker-compose.yml
```

---

## AWS S3 configuration (optional)

The contact form can optionally upload submissions to an S3 bucket. Configure credentials at `http://localhost/config.php` after logging in, or edit `main/MainApp/trading/aws.json` directly.

The file ships with placeholder values. Replace `REPLACE_WITH_YOUR_IAM_KEY` and `REPLACE_WITH_YOUR_IAM_SECRET` with real credentials if you want S3 uploads to work.
