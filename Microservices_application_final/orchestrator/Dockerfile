FROM python:3.11-slim
WORKDIR /app
COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY database/ /app/database/
COPY orchestrator/orchestrator.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 5002
CMD ["python", "orchestrator.py"]
