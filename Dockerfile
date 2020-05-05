FROM python:3.8-buster


RUN apt update && apt -y upgrade
RUN apt install -y python3-numpy python3-pip
RUN pip3 install dpu-utils typed-ast gitpython sentencepiece


ENV PYTHONPATH=/usr/src/

COPY src /usr/src
COPY entrypoint.py /usr/src/entrypoint.py

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["python", "/usr/src/entrypoint.py"]
