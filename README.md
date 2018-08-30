# Floe Microservice

This presents a simple key value data store with a list of ids and configurable backends.

Can use it as a python backend or as a uwsgi application in a docker container.

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
