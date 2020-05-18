FROM docker.pkg.github.com/typilus/typilus-action-docker/typilusactionenv:v1

ENV PYTHONPATH=/usr/src/
ADD https://github.com/typilus/typilus-action/releases/download/v0.1/typilus20200507.pkl.gz /usr/src/model.pkl.gz
COPY src /usr/src
COPY entrypoint.py /usr/src/entrypoint.py

ENTRYPOINT ["python", "/usr/src/entrypoint.py"]
