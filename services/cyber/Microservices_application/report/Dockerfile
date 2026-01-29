FROM python:3.11-slim

WORKDIR /app

COPY report.py .
COPY report_scored.py .
COPY ../common ./common

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "report.py"]
