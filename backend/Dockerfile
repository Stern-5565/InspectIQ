# Production image for the FastAPI backend.
#
# Base is pinned to python:3.14-slim-bookworm (not the floating python:3.14-slim tag)
# deliberately: the ODBC driver install below adds Microsoft's apt repo for Debian 12
# ("bookworm") specifically, and a floating tag could silently move to a newer Debian codename
# Microsoft's repo doesn't have an entry for yet, breaking the build with no code change on our
# side. Same base PropertyManager's own backend/Dockerfile uses - identical stack, identical
# reasoning.
FROM python:3.14-slim-bookworm

# pyodbc (requirements.txt) needs a Microsoft ODBC Driver for SQL Server - a system package, not
# something `pip install` can provide. Steps follow Microsoft's own documented install process:
# https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
#
# msodbcsql18, NOT msodbcsql17 - a lesson already paid for once on PropertyManager's own
# deployment, applied here from the start rather than rediscovered: msodbcsql17 (last updated
# years before this Debian 12/OpenSSL 3.0 base image existed) hangs the TLS handshake against
# Azure SQL on this base image until "Login timeout expired" - Windows' SChannel TLS stack
# (used by every local dev/test run of this app so far) masks this entirely, since the failure
# is specific to Linux+OpenSSL 3.0's stricter default security level. msodbcsql18 is the
# actively maintained driver built against modern OpenSSL. app/core/config.py's DB_DRIVER is
# already just a configurable setting (not hardcoded anywhere else) - the only other change
# needed is setting DB_DRIVER=ODBC Driver 18 for SQL Server wherever this image actually runs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -sSL https://packages.microsoft.com/config/debian/12/prod.list \
        -o /etc/apt/sources.list.d/mssql-release.list \
    && sed -i 's#deb \[arch=amd64,armhf,arm64\]#deb [arch=amd64,armhf,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg]#' \
        /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev \
    && apt-mark manual libgssapi-krb5-2 \
    # ^ libgssapi-krb5-2 is a real runtime dependency of the driver, but apt installed it
    # earlier as a dependency of curl in the SAME command and doesn't know the driver needs it
    # too - without this line, `apt-get autoremove` below (after curl/gnupg are purged) silently
    # removes it, and pyodbc fails at runtime with a misleading "file not found" error pointing
    # at the DRIVER .so itself, not the actual missing dependency (the exact bug PropertyManager
    # hit and fixed the same way).
    && apt-get purge -y curl gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Only requirements.txt (runtime deps) - never requirements-dev.txt (pytest/httpx), which has
# no place in the production image.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# scripts/ (seed_demo_users.py) is deliberately NOT copied - demo accounts with a known shared
# password must never exist in a production image, same rule PropertyManager's deployment
# followed. uploads/ isn't copied either - production media goes to Azure Blob Storage, not the
# container's own ephemeral filesystem (a container restart would silently lose anything saved
# there, on top of it never having been scoped for that use).

# No .env is copied in - every setting comes from Container Apps' own secrets/environment
# variables at runtime. See docs/DEPLOYMENT_GUIDE.md for the full variable list.
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
