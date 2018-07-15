# -*- coding: utf-8-*-

from __future__ import absolute_import
from . import config
import uuid
import requests


def getUUID():
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return ":".join([mac[e:e+2] for e in range(0, 11, 2)])


def report(t):
    config.init()
    to_report = config.get('statistic', True)
    if to_report:
        try:
            persona = config.get("robot_name", 'DINGDANG')
            url = 'http://bbs.hahack.com:8022/statistic'
            payload = {'type': str(t), 'uuid': getUUID(), 'name': persona}
            requests.post(url, data=payload)
        except Exception:
            return
