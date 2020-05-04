FROM python:3.8-alpine

RUN pip install dpu-utils typed-ast gitpython

ENV PYTHONPATH=/usr/src/

COPY src /usr/src
COPY entrypoint.py /usr/src/entrypoint.py

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY entrypoint.sh /entrypoint.sh

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]
