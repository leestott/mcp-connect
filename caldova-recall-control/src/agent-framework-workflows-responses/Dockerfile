FROM python:3.13-slim

RUN groupadd --gid 10001 caldova && \
    useradd --uid 10001 --gid caldova --create-home --shell /usr/sbin/nologin caldova

WORKDIR /app

COPY --chown=10001:10001 . user_agent/
WORKDIR /app/user_agent

RUN if [ -f requirements.lock ]; then \
        pip install --no-cache-dir --require-hashes -r requirements.lock; \
    else \
        echo "No requirements.lock found"; \
    fi

RUN python -m venv /opt/caldova-mcp && \
    /opt/caldova-mcp/bin/pip install --no-cache-dir --require-hashes -r requirements-mcp.lock

# Remove build tooling from both interpreters: neither pip, setuptools, nor wheel
# is needed at runtime, and their vendored trees are the only remaining source of
# fixable high-severity CVEs in the image scan.
RUN python -m pip uninstall -y pip setuptools wheel || true; \
    /opt/caldova-mcp/bin/python -m pip uninstall -y pip setuptools wheel || true; \
    rm -rf /root/.cache/pip /home/caldova/.cache/pip

ENV CALDOVA_MCP_PYTHON=/opt/caldova-mcp/bin/python

EXPOSE 8088

# Precompile Python bytecode at build time so cold starts don't pay for it.
# These base images ship almost none of the standard library precompiled
# (~2% of stdlib .py files, on both Debian-slim and Azure Linux), so without
# this every new container recompiles hundreds of stdlib modules on first
# import. Dependencies are best-effort (`|| true`) so a stray unparsable file
# vendored by a third-party package can't fail the build; application code is
# compiled strictly so a syntax error surfaces at build time rather than at
# container start.
# PYTHONDONTWRITEBYTECODE is cleared for these commands only: it blocks
# bytecode *writes*, not *reads*, so images that set it still benefit.
RUN PYTHONDONTWRITEBYTECODE= python -m compileall -q $(python -c "import sysconfig as s; print(s.get_paths()['stdlib'], s.get_paths()['purelib'])") || true; \
    PYTHONDONTWRITEBYTECODE= python -m compileall -q .

USER 10001:10001

CMD ["python", "main.py"]