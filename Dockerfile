FROM python:3.8-buster


RUN apt update && apt -y upgrade
RUN apt install -y python3-numpy python3-pip python3-requests
RUN pip3 install dpu-utils typed-ast gitpython sentencepiece PyGithub
RUN pip3 install torch==1.5.0+cpu torchvision==0.6.0+cpu -f https://download.pytorch.org/whl/torch_stable.html
RUN pip3 install torch-scatter==2.0.4+cpu -f https://pytorch-geometric.com/whl/torch-1.5.0.html


ENV PYTHONPATH=/usr/src/

COPY src /usr/src
COPY entrypoint.py /usr/src/entrypoint.py

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["python", "/usr/src/entrypoint.py"]
