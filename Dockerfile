FROM python:3.8-slim-buster

WORKDIR /worker

COPY . /worker

RUN [ "python", "/worker/setup.py", "install" ]

