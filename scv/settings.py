#!/usr/bin/env python

"""Simple key-value app configuration settings."""

from google.appengine.ext import ndb


class Settings(ndb.Model):
  value = ndb.JsonProperty()


def get(key):
  entity = Settings.get_by_id(key)
  if entity:
    return entity.value
  return None


def set(key, value):
  entity = Settings(id=key, value=value)
  entity.put()
