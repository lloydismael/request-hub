FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app

COPY requirements.txt ./
RUN apk upgrade --no-cache \
    && apk add --no-cache ca-certificates tini \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN addgroup -S -g "${APP_GID}" app \
    && adduser -S -D -u "${APP_UID}" -G app -h /app app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app \
    && chmod +x /app/entrypoint.sh

USER app

ENTRYPOINT ["/sbin/tini", "--", "/app/entrypoint.sh"]
