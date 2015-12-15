import logging

from bottle import request

from ..heartbeat import process_heartbeat


def collect_heartbeat():
    data = request.forms.get('stream')
    process_heartbeat(data)
    return 'OK'
