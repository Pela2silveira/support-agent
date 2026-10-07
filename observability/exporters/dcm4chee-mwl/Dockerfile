FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 -r requirements.txt
COPY exporter.py .

EXPOSE 9100
CMD ["python", "-u", "exporter.py"]
