FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Pre-pull gemma4:4b at build time so the model is ready on first startup
RUN /bin/bash -c '\
    ollama serve & \
    until ollama list >/dev/null 2>&1; do sleep 1; done; \
    ollama pull gemma4:4b; \
    pkill -f "ollama serve" || true'

EXPOSE 11434

CMD ["ollama", "serve"]
