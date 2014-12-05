#!/usr/bin/env python

"""Main application handler."""

import os
import webapp2
from scv import rpc
from scv.services import github
from scv.services import grow

IS_DEVAPPSERVER = os.getenv('SERVER_SOFTWARE', '').startswith('Dev')
DEBUG = IS_DEVAPPSERVER


class MainHandler(webapp2.RequestHandler):
  """Main frontend handler."""

  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.write('Hello, world!')


rpc.register_service('GitHubService', github.GitHubService())
rpc.register_service('GrowService', grow.GrowService())
app = webapp2.WSGIApplication([
    ('/_/github/webhook', github.GitHubWebhookHandler),
    ('/_/rpc', rpc.JsonRpcHandler),
    ('/_/tasks/deploy', grow.GrowDeployTaskHandler),
    ('/', MainHandler),
], debug=DEBUG)
