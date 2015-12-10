import time
import logging

from bottle import request, abort

from ..core.serializer import from_stream_str


def process_heartbeat(country_code, ip_address, data):
    try:
        data = from_stream_str(data, version=1)
    except (AttributeError, ValueError):
        import traceback
        traceback.print_exc()
        # Request body is either not available at all, or the JSON is malformed
        abort(400, 'Invalid data')

    logging.info('Received %s data points from %s', len(data), ip_address)

    for d in data:
        process_data(country_code, request.remote_addr, d)

    logging.info('Finished storing all data points')

    return 'OK'


def service_ok(signal_lock, bitrate, service_lock):
    if not signal_lock:
        # This is always OK because if there's no lock, we don't know if the
        # service is alright.
        return True
    if not bitrate:
        return False
    if not service_lock:
        # This is disputable, because transfers could be empty for reasons
        # other than broadcast problem (e.g., broken cache directory, full
        # disk). We'll go with this for now, and change later if necessary.
        return False
    return True


def process_data(country_code, ip_addr, data):
    db = request.db.monitoring

    status = service_ok(data['signal_lock'], data['bitrate'],
                        data['service_lock'])

    payload = {
        'ip': ip_addr,
        'location': country_code,
        'client_id': data['client_id'],
        'signal_lock': data['signal_lock'],
        'service_lock': data['service_lock'],
        'signal_strength': data['signal_strength'],
        'bitrate': data['bitrate'],
        'snr': data['snr'],
        'service_ok': status,
        'tuner_vendor': data['tuner_vendor'],
        'tuner_model': data['tuner_model'],
        'tuner_preset': data['tuner_preset'],
        'carousels_count': data['carousel_count'],
        'carousels_status': data['carousel_status'],
        'timestamp': data['timestamp'],
        'reported': time.time(),
    }

    qry = db.Insert('stats', cols=payload.keys())
    db.execute(qry, payload)
    return status
