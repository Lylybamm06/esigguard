FROM python:3.11-slim

WORKDIR /app

COPY orchestrator.py .
COPY requirements.txt .

RUN pip install --no-cache-dir flask requests mysql-connector-python

# Exposer le port
EXPOSE 5106

CMD ["python", "orchestrator.py"]

