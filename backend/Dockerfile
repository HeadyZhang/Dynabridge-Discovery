FROM python:3.12-slim

WORKDIR /app

# Install system deps (LibreOffice for PPTX preview, Chromium for Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000
CMD ["python", "main.py"]
