#!/usr/bin/env python

"""GitHub service."""

import base64
import hashlib
import hmac
import json
import logging
import os
import webapp2
from google.appengine.api import urlfetch
from scv import rpc
from scv import settings

__all__ = ('GitHubService',)

GITHUB_API_HOST = 'https://api.github.com'
RpcMethod = rpc.RpcMethod

class Error(Exception):
  pass


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

  @RpcMethod
  def GetFile(self, path, ref='master'):
    url_path = os.path.join('/repos', self.get_repo(), 'contents', path)
    url = GITHUB_API_HOST + url_path
    headers = {
        'Authorization': 'token {}'.format(self.get_access_token()),
    }
    response = urlfetch.fetch(url, headers=headers, deadline=10)
    if response.status_code != 200:
      raise Error(response.content)
    return json.loads(response.content)

  @RpcMethod
  def WriteFile(self, path, message, content, sha=None, encoding=None,
      branch='master', commiter=None):
    """Writes content to a file.

    Args:
      path: File path.
      message: Commit message.
      content: File content.
      sha: If updating an existing file, the blob SHA of the file being
          replaced.
      encoding: Should be "base64". If the content isn't encoded, the content
          will be base64 encoded before sending to GitHub.
      branch: The branch name.
      commiter: A dict of "name" and "email".
    """
    url_path = os.path.join('/repos', self.get_repo(), 'contents', path)
    url = GITHUB_API_HOST + url_path
    headers = {
        'Authorization': 'token {}'.format(self.get_access_token()),
        'Content-Type': 'application/json',
    }
    # The GitHub API requires the content to be base64 encoded.
    if encoding != 'base64':
      content = base64.b64encode(content)
    data = {
        'message': message,
        'content': content,
    }
    if sha:
      data['sha'] = sha
    if commiter:
      data['commiter'] = commiter
    payload = json.dumps(data)
    response = urlfetch.fetch(url, method=urlfetch.PUT, headers=headers,
        payload=payload, deadline=10)
    if response.status_code != 200 and response.status_code != 201:
      raise Error(response.content)
    return json.loads(response.content)

  @RpcMethod
  def DeleteFile(self, path, message, sha, branch='master', commiter=None):
    # TODO(stevenle): this API doesn't actually work yet, because the urlfetch
    # service doesn't allow request bodies in DELETE requests.
    url_path = os.path.join('/repos', self.get_repo(), 'contents', path)
    url = GITHUB_API_HOST + url_path
    headers = {
        'Authorization': 'token {}'.format(self.get_access_token()),
        'Content-Type': 'application/json',
    }
    data = {
        'message': message,
        'sha': sha,
    }
    if commiter:
      data['commiter'] = commiter
    payload = json.dumps(data)
    response = urlfetch.fetch(url, method=urlfetch.DELETE, headers=headers,
        payload=payload, deadline=10)
    if response.status_code != 200:
      raise Error(response.content)
    return json.loads(response.content)

  def get_access_token(self):
    return settings.get('github_access_token')

  def get_repo(self):
    return settings.get('github_repo')


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
