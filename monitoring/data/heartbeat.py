"""
heartbeat.py: Processes and stores heartbeat information
"""

import time

from bottle import request


HEARTBEAT_PERIOD = 60  # should be same as in monitoring client


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
    received_at = time.time()
    # reversed because last entry is the newest one
    for (idx, entry) in enumerate(reversed(data)):
        # approximate timestamp based on time of heartbeat reception by
        # subtracting the same interval that the client application uses from
        # the reception time, making it:
        # 0th entry ~= now
        # 1st entry ~= now - HEARTBEAT_PERIOD
        # 2nd entry ~= now - 2 * HEARTBEAT_PERIOD
        timestamp = received_at - idx * HEARTBEAT_PERIOD
        status = service_ok(entry['signal_lock'],
                            entry['bitrate'],
                            entry['transfers'])
        payload = {
            'ip': ip_addr,
            'location': country_code,
            'client_id': entry['client_id'],
            'service_id': entry['service_id'],
            'pid': entry['pid'],
            'signal_lock': entry['signal_lock'],
            'bitrate': entry['bitrate'],
            'snr': entry['snr'],
            'transfers': entry['transfers'],
            'sat_config': entry['sat_config'],
            'service_ok': status,
            'timestamp': timestamp,
            'processing_time': entry['processing_time'],
            'reported': time.time(),
        }
        qry = db.Insert('stats', cols=payload.keys())
        db.execute(qry, payload)
