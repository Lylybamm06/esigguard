FROM python:3.11-slim
WORKDIR /app
COPY auth/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install python-dateutil
COPY database/ /app/database/
COPY auth/auth_service.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 5003
CMD ["python", "auth_service.py"]
