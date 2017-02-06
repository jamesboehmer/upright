FROM alpine:3.5

RUN apk update
RUN apk add bash
RUN apk add git
RUN apk add curl
RUN apk add readline
RUN apk add vim
RUN apk add python3=3.5.2-r9

ADD requirements.txt /tmp/
RUN pip3 install --upgrade pip setuptools
RUN pip3 install -r /tmp/requirements.txt
