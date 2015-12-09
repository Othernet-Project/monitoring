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
    data = request.body
    ip_addr = request.remote_addr
    country_code = ip_country(request.remote_addr)
    logging.info('Received %s data points from %s', len(data), ip_addr)
    process_heartbeat(country_code, request.remote_addr, data)
    logging.info('Finished storing all data points')
    return 'OK'
