FROM python:3.8-alpine

RUN pip install dpu-utils typed-ast gitpython

ENV PYTHONPATH=/usr/src/

COPY src /usr/src
COPY entrypoint.py /usr/src/entrypoint.py

ENTRYPOINT ["python", "/usr/src/entrypoint.py"]
