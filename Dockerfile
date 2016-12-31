FROM ubuntu:14.04

COPY ./src /app

RUN apt-get update -y
RUN apt-get install -y python-gtk2 python-opencv

RUN rm -rf /root/.cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

CMD ["python" "/app/main.py"]
