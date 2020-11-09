FROM python:3.8-alpine

WORKDIR /worker

COPY . /worker

RUN [ "python", "/worker/setup.py", "install" ]

