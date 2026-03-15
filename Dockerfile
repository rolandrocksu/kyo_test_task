FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

# Run email listener and FastAPI app in the same container for the demo
CMD ["sh", "-c", "python -m app.services.email_listener & uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload"]

