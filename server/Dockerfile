FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CMS_DATA_DIR=/data
WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt \
    && useradd --uid 1000 --create-home orion \
    && mkdir /data && chown orion:orion /data
COPY --chown=orion:orion . .
USER orion
EXPOSE 8000
CMD ["sh", "server/start.sh"]
