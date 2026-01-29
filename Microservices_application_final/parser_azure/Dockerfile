FROM python:3.11-slim
WORKDIR /app
COPY parser_azure/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY database/ /app/database/
COPY parser_azure/parser_azure.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 5001
CMD ["python", "parser_azure.py"]
