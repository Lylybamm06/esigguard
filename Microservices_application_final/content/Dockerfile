FROM python:3.11-slim
WORKDIR /app
COPY content/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY database/ /app/database/
COPY content/content_service.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 5006
CMD ["python", "content_service.py"]
