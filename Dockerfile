# SPDX-FileCopyrightText: 2021 UdS AES <https://www.uni-saarland.de/lehrstuhl/frey.html>
# SPDX-License-Identifier: MIT


# Start at current release, but specify version explicitly
FROM python:3.8-slim-buster AS production

# Provide metadata according to namespace suggested by http://label-schema.org/
LABEL org.label-schema.schema-version="1.0.0-rc.1"
LABEL org.label-schema.name="simaas-worker"
LABEL org.label-schema.description="SIMaaS-Worker Handling Jobs Distributed via Celery"
LABEL org.label-schema.vendor="UdS AES"
LABEL org.label-schema.vcs-url="https://github.com/UdSAES/simaas-worker"

# Install dependencies on the base image level
RUN apt-get update && apt-get install -y \
    git \
  && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install pipenv

# Prepare directories and environment
ENV USER=celery
ENV WORKDIR=/home/$USER
RUN adduser $USER --system --group --disabled-password --home $WORKDIR
WORKDIR $WORKDIR

# Install app-level dependencies
COPY --chown=$USER:$USER Pipfile $WORKDIR
COPY --chown=$USER:$USER Pipfile.lock $WORKDIR
RUN pipenv install --system --deploy

# Switch to non-root user to complicate privilege escalation
USER $USER

# Install application code by copy-pasting the source to the image
# (subject to .dockerignore)
COPY --chown=$USER:$USER worker $WORKDIR/worker/

# Store reference to commit in version control system in image
ARG VCS_REF
LABEL org.label-schema.vcs-ref=$VCS_REF

# Unless overridden, run this command upon instantiation
ENTRYPOINT [ "celery", "--app=worker", "worker"]
