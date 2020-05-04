FROM python:3.8-buster


RUN apt update && apt -y upgrade
RUN apt install -y python3-numpy python3-pip
RUN pip3 install dpu-utils typed-ast gitpython


ENV PYTHONPATH=/usr/src/

COPY src /usr/src
COPY entrypoint.py /usr/src/entrypoint.py

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY entrypoint.sh /entrypoint.sh

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["python", "/usr/src/entrypoint.py"]
