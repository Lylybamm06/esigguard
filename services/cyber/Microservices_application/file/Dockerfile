FROM python:3.11-slim
WORKDIR /app
COPY file/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY database/ /app/database/
COPY file/file_service.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 5005
CMD ["python", "file_service.py"]
