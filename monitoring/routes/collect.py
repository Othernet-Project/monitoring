import json
import logging

from bottle import request, abort

from ..ext import geoip
from ..data import heartbeat


def process_heartbeat():
    try:
        data = json.load(request.body)
    except (AttributeError, ValueError):
        # Request body is either not available at all, or the JSON is malformed
        abort(400, 'Invalid data')

    ip_addr = request.remote_addr
    country_code = geoip.ip_country(request.remote_addr)

    logging.info('Received %s data points from %s', len(data), ip_addr)

    for d in data:
        heartbeat.process_data(country_code, request.remote_addr, d)

    logging.info('Finished storing all data points')

    return 'OK'


def route(config):
    return (
        (
            '/heartbeat/',
            'POST',
            process_heartbeat,
            'api:heartbeat',
            {}
        ),
    )
