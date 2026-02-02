FROM python:3.11-slim
WORKDIR /app
COPY lien/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY database/ /app/database/
COPY lien/lien_service.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 5004
CMD ["python", "lien_service.py"]
