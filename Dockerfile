
FROM 72squared/microbase:latest

MAINTAINER john@marcopolo.me

# setup all the configfiles
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/sites-available/default
COPY supervisor.conf /etc/supervisor/conf.d/

# pip install packages
COPY ./*requirements.txt /srv/
RUN /opt/venv/bin/pip install -r /srv/requirements.txt

# add (the rest of) our code
COPY ./run.py /srv/
COPY ./pytest.ini /srv/
COPY ./test.py /srv/
COPY ./uwsgi.ini /srv/
COPY ./floe/ /srv/floe/

RUN mkdir -p /srv/__pycache__/__pycache__ && chmod -R 1777 /srv/__pycache__ && chmod -R 1777 /srv/__pycache__/__pycache__

EXPOSE 8080

CMD ["supervisord", "-n"]