#!/usr/bin/env python

"""Grow service."""

import json
import logging
import webapp2
from scv import rpc
from scv import settings
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch

__all__ = ('GrowService',)

RpcMethod = rpc.RpcMethod


class GrowService(object):
  """Grow RPC service."""

  @RpcMethod
  def Deploy(self, commit_id, deploy_target='default'):
    """Queues a commit for deploy."""
    self.deploy(commit_id, deploy_target=deploy_target)
    return {'success': True}

  @RpcMethod
  def SetDeployServiceHost(self, host):
    settings.set('deploy_service_host', host)
    return {'success': True}

  @RpcMethod
  def SetDeployTarget(self, branch, deploy_target):
    """Configures the deploy target for a branch.

    By setting the deploy target, any changes to the branch will automatically
    trigger a "grow deploy" to that deploy target.

    Args:
      branch: The name of the git branch.
      deploy_target: The grow deploy target.
    """
    deploy_targets = settings.get('deploy_targets') or {}
    deploy_targets[branch] = deploy_target
    settings.set('deploy_targets', deploy_targets)
    return {'success': True}

  def get_deploy_target(self, branch):
    """Returns the deploy target for a branch."""
    deploy_targets = settings.get('deploy_targets') or {}
    return deploy_targets.get(branch)

  def deploy(self, commit_id, deploy_target='default'):
    q = taskqueue.Queue('deploy-queue')
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps({
        'host': 'github',
        'repo': settings.get('github_repo'),
        'commit_id': commit_id,
        'github_access_token': settings.get('github_access_token'),
        'deploy_target': deploy_target,
    })
    task = taskqueue.Task(
        url='/_/tasks/deploy', headers=headers, payload=payload)
    q.add(task)
    logging.info('queued for deploy: %s', commit_id)


class GrowDeployTaskHandler(webapp2.RequestHandler):

  def post(self):
    data = json.loads(self.request.body)

    url = '{}/_/rpc'.format(settings.get('deploy_service_host'))
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps({
        'method': 'GrowDeployService.Deploy',
        'params': [data],
    })
    response = urlfetch.fetch(
        url, method=urlfetch.POST, headers=headers, payload=payload,
        deadline=30)

    commit_id = data['commit_id']
    if response.status_code == 200:
      logging.info('deployed %s!', commit_id)
    else:
      logging.error('failed to deploy %s. error code: %d, response:\n%s',
          commit_id, response.status_code, response.content)
