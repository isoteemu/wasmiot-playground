FROM mcr.microsoft.com/devcontainers/python:0-3.11-buster AS base

RUN su vscode -c "mkdir -p /home/vscode/.vscode-server/extensions"

FROM base AS wasm

# Install rust using devcontainer script
ENV CARGO_HOME=/usr/local/cargo \
    RUSTUP_HOME=/usr/local/rustup
ENV PATH=${CARGO_HOME}/bin:${PATH}
COPY .devcontainer/library-scripts/rust.sh /tmp/library-scripts/
RUN apt-get update && bash /tmp/library-scripts/rust.sh "${CARGO_HOME}" "${RUSTUP_HOME}"

RUN ${CARGO_HOME}/bin/rustup target add wasm32-wasi

FROM wasm AS wasmtime

# Install wasmtime
RUN apt update && \
    apt install curl ca-certificates xz-utils -y -qq --no-install-recommends && \
    curl https://wasmtime.dev/install.sh -sSf | bash && \
    pip install wasmtime
