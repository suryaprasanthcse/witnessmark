# syntax=docker/dockerfile:1.7
# Published-binary build path allowed by the Omnigraph target blueprint.
# The caller supplies an official release archive whose SHA-256 is verified
# before either executable is installed.
FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2

ARG OMNIGRAPH_VERSION
ARG OMNIGRAPH_SOURCE_COMMIT
ARG OMNIGRAPH_ARCHIVE_SHA256

LABEL org.opencontainers.image.title="Witnessmark Omnigraph test image" \
      org.opencontainers.image.version="${OMNIGRAPH_VERSION}" \
      org.opencontainers.image.revision="${OMNIGRAPH_SOURCE_COMMIT}" \
      org.opencontainers.image.source="https://github.com/ModernRelay/omnigraph"

# The binaries build their S3 client with the system trust store; without a CA
# bundle it fails to initialise ("storage_root_invalid"), even for plain HTTP.
# Upstream's own Dockerfile installs the same package.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY omnigraph-linux-x86_64.tar.gz /tmp/omnigraph-linux-x86_64.tar.gz

RUN echo "${OMNIGRAPH_ARCHIVE_SHA256}  /tmp/omnigraph-linux-x86_64.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/omnigraph-linux-x86_64.tar.gz -C /usr/local/bin omnigraph omnigraph-server \
    && chmod 0755 /usr/local/bin/omnigraph /usr/local/bin/omnigraph-server \
    && rm /tmp/omnigraph-linux-x86_64.tar.gz \
    && omnigraph --version \
    && omnigraph-server --help >/dev/null

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/omnigraph-server"]
