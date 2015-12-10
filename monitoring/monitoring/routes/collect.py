import logging

from bottle import request

from ..heartbeat import process_heartbeat


def ip_country(addr):
    gp = request.app.supervisor.exts.geoip
    cc = gp.country_code_by_addr(addr)
    if cc is None:
        return cc
    return cc.lower()


def collect_heartbeat():
    data = request.forms.get('stream')
    ip_addr = request.remote_addr
    country_code = ip_country(request.remote_addr)
    process_heartbeat(country_code, request.remote_addr, data)
    return 'OK'
