FROM python:3.13-slim AS deps
ENV PATH="/opt/venv/bin:$PATH"
RUN python -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM deps AS test-deps
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt

FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
WORKDIR /srv/catalog
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
USER 10001:10001

FROM base AS test
COPY --from=test-deps /opt/venv /opt/venv
COPY pyproject.toml .
COPY tests ./tests
CMD ["pytest", "-p", "no:cacheprovider"]

FROM base AS runtime
COPY --from=deps /opt/venv /opt/venv
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
