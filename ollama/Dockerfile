FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

ENV OLLAMA_DEBUG=2

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        zstd \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Pre-pull llama3.2 at build time so the model is ready on first startup
RUN ollama serve & \
    sleep 5 &&
    curl --retry 10 --retry-connrefused -s http://localhost:11434 || true && \
    ollama pull llama3.2 && \
    pkill ollama || true

EXPOSE 11434

CMD ["ollama", "serve"]
