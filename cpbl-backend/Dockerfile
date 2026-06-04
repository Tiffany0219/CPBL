FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    CPBL_HOST=0.0.0.0 \
    FLASK_DEBUG=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        chromium-driver \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY cpbl-backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY cpbl-backend/ ./

RUN mkdir -p instance

EXPOSE 10000

CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 180"]
