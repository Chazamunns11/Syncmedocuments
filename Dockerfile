# Run the value betting bot continuously on a small VPS.
#
#   docker build -t valuebot .
#   docker run -d --restart=always --name valuebot \
#     --env-file .env -v "$PWD/data:/data" valuebot \
#     go --budget 1000 --stake 10
#
# Bankroll/CLV history persists in the mounted /data volume (db_path/csv_path
# point there via config). Real betting still requires live:true + creds.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist the SQLite/CSV under /data (set db_path: /data/bets.db in config.yaml).
VOLUME ["/data"]
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "run.py", "-v"]
CMD ["status"]
