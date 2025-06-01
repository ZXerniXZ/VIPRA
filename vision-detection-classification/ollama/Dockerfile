# -------- 1° stage: scarica il modello --------------------
FROM --platform=$BUILDPLATFORM ollama/ollama:latest AS downloader

# ② avviamo il daemon in background, aspettiamo che sia pronto, poi pull
RUN ollama serve & \
    until ollama list >/dev/null 2>&1 ; do sleep 1 ; done && \
    ollama pull gemma3:1b

# -------- 2° stage: immagine finale leggera ---------------
FROM ollama/ollama:latest
COPY --from=downloader /root/.ollama /root/.ollama

# (facoltativo) metadati utili
LABEL maintainer="zxernixz7" \
      model="gemma3:1b"

