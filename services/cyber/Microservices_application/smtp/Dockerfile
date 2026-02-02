FROM python:3.11-slim
WORKDIR /app
COPY smtp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY database/ /app/database/
COPY smtp/smtp_service.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 5007
CMD ["python", "smtp_service.py"]
