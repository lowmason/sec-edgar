FROM docker.io/library/python@sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d
# sec-edgar-ingest worker. Context: scripts/build-image-context.sh. Stage 6 builds it locally (D1);
# Stage 7 builds the release image with an ACR quick task (S7-05). The base is F1's Linux amd64 child
# digest, so the platform is never selected here. The image carries no configuration.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/home/worker
COPY requirements.lock /build/requirements.lock
COPY sec_edgar_ingest-*.whl /build/
RUN python -m pip install --require-hashes --no-deps --only-binary=:all: -r /build/requirements.lock \
 && python -m pip install --no-deps /build/sec_edgar_ingest-*.whl \
 && python -m pip check \
 && rm -rf /build \
 && mkdir -p /home/worker /tmp/sec-edgar-ingest \
 && chown 1000:1000 /home/worker /tmp/sec-edgar-ingest \
 && chmod 0700 /tmp/sec-edgar-ingest
ENV TMPDIR=/tmp/sec-edgar-ingest
USER 1000:1000
WORKDIR /home/worker
ENTRYPOINT ["sec-edgar-ingest"]
