FROM ghcr.io/astral-sh/uv:0.12.16@sha256:adc68cd785ca65ea25c0611043b0a00b4ea3a22e1b54102fc084406d888082ee AS uv
FROM python:3.13.15-alpine3.24@sha256:1a63a53928ce53d2b0baf08092a703f4840ac5dfbd61fd48802dbf48e08c801e AS dependencies
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /srv/repairhub
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-default-groups --no-install-project

FROM python:3.13.15-alpine3.24@sha256:1a63a53928ce53d2b0baf08092a703f4840ac5dfbd61fd48802dbf48e08c801e AS app
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="RepairHub" \
      org.opencontainers.image.source="https://github.com/GojicDragan/RepairHub" \
      org.opencontainers.image.revision=$VCS_REF
ENV PATH="/srv/repairhub/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/repairhub
# pip samt gebündelten Buildwerkzeugen wird nur beim Basisimage mitgeliefert.
# Die Laufzeit verwendet ausschliesslich die gesperrte venv; keine Paketinstallation.
RUN addgroup -g 10001 repairhub && adduser -D -H -u 10001 -G repairhub repairhub \
    && rm -rf /usr/local/lib/python3.13/ensurepip \
       /usr/local/lib/python3.13/site-packages/pip \
       /usr/local/lib/python3.13/site-packages/pip-*.dist-info /usr/local/bin/pip*
COPY --from=dependencies /srv/repairhub/.venv ./.venv
COPY app ./app
RUN pybabel compile -d app/translations
COPY migrations ./migrations
COPY scripts/healthcheck.py ./healthcheck.py
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "healthcheck.py"]
# Docker verwaltet den Prozess; der optionale Control-Socket würde ins
# schreibgeschützte Home-Verzeichnis schreiben.
CMD ["gunicorn", "--no-control-socket", "--bind=0.0.0.0:8000", "--workers=2", "--worker-tmp-dir=/tmp", "--forwarded-allow-ips=", "app:create_app()"]
