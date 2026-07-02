FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY balcao ./balcao
RUN pip install --no-cache-dir .

RUN useradd --create-home balcao
USER balcao

EXPOSE 8000
# forma shell de propósito: plataformas como o Render injetam $PORT
CMD uvicorn balcao.main:app --host 0.0.0.0 --port ${PORT:-8000}
