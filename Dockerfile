

FROM 72squared/microbase:latest

MAINTAINER john@marcopolo.me


# setup all the configfiles
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/sites-available/default
COPY supervisor.conf /etc/supervisor/conf.d/

RUN cd /opt && wget -q "https://bitbucket.org/pypy/pypy/downloads/pypy3.6-v7.1.1-linux64.tar.bz2" -O - | tar -xj && mv pypy3.6-v7.1.1-linux64 pypy3
RUN virtualenv -p /opt/pypy3/bin/pypy3 /opt/venv3

# pip install packages
COPY ./*requirements.txt /srv/
RUN /opt/venv3/bin/pip install -r /srv/dev-requirements.txt

# add (the rest of) our code
COPY ./run.py /srv/
COPY ./pytest.ini /srv/
COPY ./test.py /srv/
COPY ./uwsgi.ini /srv/
COPY ./floe/ /srv/floe/

RUN mkdir -p /srv/__pycache__/__pycache__ && chmod -R 1777 /srv/__pycache__ && chmod -R 1777 /srv/__pycache__/__pycache__


RUN cd /srv && /opt/venv3/bin/py.test

EXPOSE 8080
CMD ["supervisord", "-n"]
