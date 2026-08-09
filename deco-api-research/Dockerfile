FROM python:3.13-slim-bookworm

ARG BUILD_VERSION=dev
ARG BUILD_ARCH=unknown

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

ENV APP_VERSION="${BUILD_VERSION}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY src ./src
COPY run.sh /run.sh
RUN chmod 0555 /run.sh \
    && groupadd --system deco-research \
    && useradd --system --gid deco-research --no-create-home deco-research

# Supervisor mounts /data/options.json for root-only startup access. The Python
# entry point reads that file once, then immediately drops to deco-research
# before opening the ingress listener or constructing any network client.
EXPOSE 8099

CMD ["/run.sh"]
