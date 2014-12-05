#!/usr/bin/env python

"""Module for handling RPCs."""

import json
import webapp2

_services = {}


class RpcMethod(object):
  """Decorator for RPC methods."""

  def __init__(self, func):
    self.func = func

  def __call__(self, *args, **kwargs):
    return self.func(*args, **kwargs)


class JsonRpcHandler(webapp2.RequestHandler):
  """JSON-RPC 2.0 handler. See: http://www.jsonrpc.org/specification."""

  def post(self):
    try:
      data = json.loads(self.request.body)
      service_name, method_name = data['method'].split('.')
      params = data['params'][0]

      # TODO(stevenle): better error handling.
      service = get_service(service_name)
      method = getattr(service, method_name)
      if isinstance(method, RpcMethod):
        result = method(service, **params)
        self.write_json(result=result)
    except Exception as e:
      self.response.status_int = 500
      self.write_json(error=str(e))

  def write_json(self, **kwargs):
    self.response.headers['Content-Type'] = 'application/json'
    self.response.write(json.dumps(kwargs, indent=2))


def register_service(name, service):
  _services[name] = service


def get_service(name):
  return _services.get(name)
