#!/usr/bin/env python

"""GitHub service."""

import hashlib
import hmac
import json
import logging
import os
import webapp2
from scv import rpc
from scv import settings

__all__ = ('GitHubService',)

RpcMethod = rpc.RpcMethod


class GitHubService(object):

  @RpcMethod
  def SetAccessToken(self, access_token):
    """Sets the GitHub OAuth2 access token to use to access the grow pod.

    The easiest way to create an access token is to generate a personal access
    token at:

      https://github.com/settings/applications

    Args:
      access_token: GitHub OAuth2 access token.
    """
    settings.set('github_access_token', access_token)
    return {'success': True}

  @RpcMethod
  def SetWebHookSecret(self, secret):
    """Sets the secret used for GitHub webhook requests."""
    settings.set('github_webhook_secret', secret)
    return {'success': True}

  @RpcMethod
  def SetRepo(self, repo):
    """Sets the GitHub repo containing the grow pod.

    Args:
      repo: The full GitHub repo id, e.g. "myuser/myrepo".
    """
    settings.set('github_repo', repo)
    return {'success': True}


class GitHubWebhookHandler(webapp2.RequestHandler):

  def post(self):
    logging.info(self.request.body)

    # Verify signature.
    if not self.is_signature_valid():
      self.write_json(success=False)
      return

    data = json.loads(self.request.body)
    # The branch name can be derived from the last part of the "ref", e.g.:
    # refs/head/<branch name>.
    branch_name = os.path.basename(data['ref'])

    grow_service = rpc.get_service('GrowService')
    deploy_target = grow_service.get_deploy_target(branch_name)
    if deploy_target:
      # Trigger a push on the commit.
      commit_id = data['after']
      grow_service.deploy(commit_id, deploy_target=deploy_target)

    self.write_json(success=True)

  def is_signature_valid(self):
    header = self.request.headers.get('X-Hub-Signature', None)
    if not header:
      return False
    if not header.startswith('sha1='):
      return False
    signature = header[5:]

    # The GitHub webhook signature is the HMAC SHA1 hex digest with the secret
    # as its key.
    webhook_secret = str(settings.get('github_webhook_secret'))
    payload = str(self.request.body)
    hash = hmac.new(webhook_secret, payload, hashlib.sha1).hexdigest()
    return signature == hash

  def write_json(self, **kwargs):
    self.response.headers['Content-Type'] = 'application/json'
    self.response.write(json.dumps(kwargs, indent=2))
