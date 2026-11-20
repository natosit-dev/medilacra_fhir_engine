# The image deliberately runs the accepted unified application unchanged.
# Before external distribution: review third-party assets and repository licenses.
# The Python base and resolved dependencies must be pinned by digest/lock for
# fully reproducible builds; this MVP records resolved packages in the image.
FROM python:3.10-slim-bookworm
ARG MEDILACRA_SOURCE_SHA=unknown
LABEL org.opencontainers.image.title="Medilacra Unified Test Workbench" \
      org.opencontainers.image.revision="${MEDILACRA_SOURCE_SHA}"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 HOME=/home/medilacra
WORKDIR /opt/medilacra
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /home/medilacra /workspace /opt/medilacra_seed
COPY . /opt/medilacra/
RUN python -m pip install --no-cache-dir -r requirements-unified.txt \
    && python -m pip freeze > /opt/medilacra/resolved-requirements.txt \
    && for path in apps/mvp0/input apps/mvp0/data; do \
         if [ -d "$path" ]; then mkdir -p "/opt/medilacra_seed/$(dirname "$path")"; cp -a "$path" "/opt/medilacra_seed/$path"; fi; \
       done \
    && chown -R 10001:0 /home/medilacra /workspace /opt/medilacra
USER 10001:0
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).read()" || exit 1
ENTRYPOINT ["python", "deploy/entrypoint.py"]
