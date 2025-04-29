# Floe Microservice

This presents a simple key value data store with a list of ids and configurable backends.

## Configuration
You can configure docker with environmental variables.

new relic can use the standard environmental variables:

https://docs.newrelic.com/docs/agents/python-agent/installation-configuration/python-agent-configuration#environment-variables


then you can add additonal environmental vars for backends.

```
FLOE_URL_FOO='file://.floe'
FLOE_URL_BAR='file:///tmp/floe'
FLOE_URL_BAZZ='mysql://root:pass@127.0.0.1:3306/test?table=bazz'
FLOE_URL_QUUX='http://127.0.0.1:995/my_namespace'
```

## API
You can add other connectors. The interface provides the following methods:

  * get
  * get_multi
  * set
  * set_multi
  * delete
  * delete_multi
  * ids
  * flush

The ids method returns a generator to iterate.
The multi methods allow you do do batch operations on multiple keys.

## Running Locally

Due to some inconsistencies with the way request bodies are handled in different WSGI implementations, PUT requests with a missing or incorrect Content-Length header may hang (https://falcon.readthedocs.io/en/stable/user/faq.html#why-does-req-stream-read-hang-for-certain-requests).

An easy workaround for this when running the server locally is to use gunicorn rather than wsgiref.simple_server

```
$ pip install gunicorn
$ gunicorn -w 4 run:app
```

## Publishing new versions

1. Set a new version number in floe/version.py
2. `./activate` to set up and enter the project venv
3. `./publish.sh` to create source and binary distributions and upload them to pypi using the `twine` tool

Credentials for pypi are stored in 1password
