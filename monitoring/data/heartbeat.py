"""
heartbeat.py: Processes and stores heartbeat information
"""

import time

from bottle import request


def service_ok(lock, bitrate, transfers):
    if not lock:
        # This is always OK because if there's no lock, we don't know if the
        # service is alright.
        return True
    if not bitrate:
        return False
    if not transfers:
        # This is disputable, because transfers could be empty for reasons
        # other than broadcast problem (e.g., broken cache directory, full
        # disk). We'll go with this for now, and change later if necessary.
        return False


def process_data(country_code, ip_addr, data):
    db = request.db.main

    status = service_ok(data['signal_lock'], data['bitrate'],
                        data['transfers'])

    payload = {
        'ip': ip_addr,
        'location': country_code,
        'client_id': data['client_id'],
        'service_id': data['service_id'],
        'pid': data['pid'],
        'signal_lock': data['signal_lock'],
        'bitrate': data['bitrate'],
        'snr': data['snr'],
        'transfers': data['transfers'],
        'sat_config': data['sat_config'],
        'service_ok': status,
        'timestamp': data['timestamp'],
        'processing_time': data['processing_time'],
        'reported': time.time(),
    }

    qry = db.Insert('stats', cols=payload.keys())
    db.execute(qry, payload)
    return status
