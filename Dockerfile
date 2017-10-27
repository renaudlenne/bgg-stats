FROM alpine:3.6

RUN echo "http://dl-8.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && \
    apk add --no-cache python3 python3-dev&& \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    ln -s /usr/include/locale.h /usr/include/xlocale.h && \
    rm -r /root/.cache
RUN  pip3 install flask certifi urllib3

ADD bgg-stats.py /
ADD templates /templates
ADD static /static
EXPOSE 5000
CMD [ "python3", "./bgg-stats.py" ]
