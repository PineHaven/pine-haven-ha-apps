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
    && groupadd --system deco-lab \
    && useradd --system --gid deco-lab --no-create-home deco-lab

# Supervisor mounts root-owned options. The entry point reads them once and
# permanently drops privilege before opening Ingress or contacting a Deco.
EXPOSE 8099

CMD ["/run.sh"]
