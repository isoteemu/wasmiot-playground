FROM mcr.microsoft.com/devcontainers/python:0-3.11 AS base

# Install wasmtime
RUN apt update && \
    apt install curl ca-certificates xz-utils -y -qq --no-install-recommends && \
    curl https://wasmtime.dev/install.sh -sSf | bash && \
    pip install wasmtime


# Install our app
WORKDIR /app
COPY . /app

ENV PYTHONUNBUFFERED 1
RUN pip install --disable-pip-version-check -e .

FROM base AS dev

RUN pip install --disable-pip-version-check -e .[dev]

# Install rust using devcontainer script
ENV CARGO_HOME=/usr/local/cargo \
    RUSTUP_HOME=/usr/local/rustup
ENV PATH=${CARGO_HOME}/bin:${PATH}
COPY .devcontainer/library-scripts/rust.sh /tmp/library-scripts/
RUN apt-get update && bash /tmp/library-scripts/rust.sh "${CARGO_HOME}" "${RUSTUP_HOME}"

RUN ${CARGO_HOME}/bin/rustup target add wasm32-wasi

FROM dev AS devcontainer

ENV PYTHONDONTWRITEBYTECODE 1
ARG USERNAME=vscode

RUN su "${USERNAME}" -c "mkdir -p /home/${USERNAME}/.vscode-server{-insiders,}/extensions"

RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    && mkdir /commandhistory \
    && touch /commandhistory/.bash_history \
    && chown -R $USERNAME /commandhistory \
    && echo "$SNIPPET" >> "/home/$USERNAME/.bashrc"
