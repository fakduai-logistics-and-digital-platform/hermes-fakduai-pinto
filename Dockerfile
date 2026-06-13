FROM python:3.11-slim AS base

RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
      ca-certificates \
      curl \
      git \
    && rm -rf /var/lib/apt/lists/*

# Install Hermes Agent
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir hermes-agent || \
    (curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash && \
     pip install --no-cache-dir httpx pyyaml)

# Install Python deps for Pinto plugin
RUN pip install --no-cache-dir httpx pyyaml

# Copy Pinto adapter plugin from adapter repo
ARG PINTO_ADAPTER_REPO=https://github.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes.git
ARG PINTO_ADAPTER_REF=main

COPY scripts/patch-pinto-for-podman.py /tmp/patch-pinto-for-podman.py
COPY scripts/patch-pinto-plugin-yaml.py /tmp/patch-pinto-plugin-yaml.py
COPY scripts/patch-api-server-for-pinto-podman.py /tmp/patch-api-server-for-pinto-podman.py
COPY scripts/patch-openai-image-provider.py /tmp/patch-openai-image-provider.py

RUN python3 /tmp/patch-api-server-for-pinto-podman.py
RUN python3 /tmp/patch-openai-image-provider.py

RUN git clone --depth 1 --branch "${PINTO_ADAPTER_REF}" "${PINTO_ADAPTER_REPO}" /tmp/pinto-adapter \
    && mkdir -p /opt/hermes-pinto-plugin \
    && cp /tmp/pinto-adapter/adapter.py /opt/hermes-pinto-plugin/adapter.py \
    && cp /tmp/pinto-adapter/plugin.yaml /opt/hermes-pinto-plugin/plugin.yaml \
    && cp /tmp/pinto-adapter/__init__.py /opt/hermes-pinto-plugin/__init__.py \
    && python3 /tmp/patch-pinto-for-podman.py \
    && python3 /tmp/patch-pinto-plugin-yaml.py \
    && rm -rf /tmp/pinto-adapter /tmp/patch-pinto-for-podman.py /tmp/patch-pinto-plugin-yaml.py /tmp/patch-api-server-for-pinto-podman.py /tmp/patch-openai-image-provider.py

# Copy scripts
COPY scripts/docker-entrypoint.sh /usr/local/bin/hermes-pinto-entrypoint
COPY scripts/bootstrap-hermes-config.py /usr/local/bin/bootstrap-hermes-config.py

RUN chmod 755 /usr/local/bin/hermes-pinto-entrypoint \
    && sed -i 's/\r$//' /usr/local/bin/hermes-pinto-entrypoint

ENV HERMES_HOME=/root/.hermes
ENV HOME=/root
ENV API_SERVER_HOST=0.0.0.0

EXPOSE 8642

ENTRYPOINT ["hermes-pinto-entrypoint"]
CMD ["hermes", "gateway", "run"]
