FROM python:3.12-slim-bookworm

ARG CODEQL_VERSION=v2.25.4

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CODEQL_HOME=/opt/codeql \
    CODEQL_REPO=/opt/codeql-repo \
    PATH="/opt/codeql:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        unzip \
        zstd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

RUN curl -fsSL -o codeql.zip "https://github.com/github/codeql-cli-binaries/releases/download/${CODEQL_VERSION}/codeql-linux64.zip" \
    && unzip -q codeql.zip -d /opt \
    && rm codeql.zip \
    && git clone --depth 1 --branch "codeql-cli/${CODEQL_VERSION}" https://github.com/github/codeql.git "${CODEQL_REPO}"

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

CMD ["python", "run_experiments.py", "--help"]
