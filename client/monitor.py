#!/usr/bin/python2

"""
monitor.py: Monitor ONDD internal state and report to remote host

Copyright 2014-2015, Outernet Inc.

Some rights reserved.

This software is free software licensed under the terms of GPLv3. See COPYING
file that comes with the source code, or http://www.gnu.org/licenses/gpl.txt.
"""

import os
import sys
import uuid
import time
import json
import signal
import socket
import syslog
import hashlib
import argparse
from urllib import urlencode
from urllib2 import urlopen
import xml.etree.ElementTree as ET
from contextlib import contextmanager

import pyudev

from monitoring.core.serializer import to_stream_str
from monitoring.core.satdata import PRESETS, COMPARE_KEYS

LOG_HANDLE = 'outernet.monitor'
ONDD_SOCKET_CONNECT_RETRIES = 3
ONDD_SOCKET_CONNECT_TIMEOUT = 5  # 5 seconds per try
ONDD_SOCKET_TIMEOUT = 20.0
ONDD_SOCKET_BUFF = 2048
ONDD_SOCKET_ENCODING = 'utf8'
HEARTBEAT_PERIOD = 60  # 1 minute
TRANSMIT_PERIOD = 5 * 60  # 5 minutes
NULL_BYTE = b'\0'


def generate_key(path):
    """ Generate client key if it does not exist, or return existing key """
    if os.path.exists(path):
        with open(path, 'r') as f:
            key = f.read()
            if key:
                return key
    key = str(uuid.uuid4())
    with open(path, 'w') as f:
        f.write(key)
    return key


def exit(pid):
    def exiter(*args, **kwargs):
        if 'code' in kwargs:
            code = kwargs['code']
        else:
            code = 0

        try:
            os.unlink(pid)
        except (OSError, IOError):
            pass

        sys.exit(code)
    return exiter


def xml_path(path):
    return '<get uri="{}"/>'.format(path)


def sat_ident(delivery, freq, modulation, symb, voltage, tone):
    sha1 = hashlib.sha1()
    sha1.update(delivery + freq + modulation + symb + voltage + tone)
    return sha1.hexdigest()[:7]


def create_socket():
    """ Create a standard UNIX socket object """
    sock = socket.socket(socket.AF_UNIX)
    sock.settimeout(ONDD_SOCKET_TIMEOUT)
    return sock


def test_connection(path):
    """ Try connection until it succeeds """
    sock = create_socket()
    connected = False
    while not connected:
        try:
            sock.connect(path)
            connected = True
        except socket.error:
            time.sleep(ONDD_SOCKET_CONNECT_TIMEOUT)
    return sock


@contextmanager
def connection(path):
    """ Context manager that connects to given socket and returns coket object
    """
    sock = test_connection(path)
    try:
        yield sock
    finally:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()


def read(sock):
    idata = data = sock.recv(ONDD_SOCKET_BUFF)
    while idata and NULL_BYTE not in idata:
        idata = sock.recv(ONDD_SOCKET_BUFF)
        data += idata
    return data[:-1].decode(ONDD_SOCKET_ENCODING)


def get_data(socket_path, ipc_path):
    """ Get XML response from specified path """
    with connection(socket_path) as sock:
        payload = xml_path(ipc_path) + NULL_BYTE
        sock.send(payload)
        data = read(sock)
    return ET.fromstring(data.encode('utf8'))


def get_text(root, xpath, default=''):
    try:
        return root.find(xpath).text
    except AttributeError:
        return default


def get_tuner_data(unknown='0000'):
    ctx = pyudev.Context()
    try:
        dvb = list(ctx.list_devices(subsystem='dvb'))[0]
        dvb_usb = dvb.parent
        vid = dvb_usb.get('ID_VENDOR_ID', unknown)
        mid = dvb_usb.get('ID_MODEL_ID', unknown)
        return (vid, mid)
    except IndexError:
        return (unknown, unknown)


def get_carousal_data(transfers_data):
    transfers_node = transfers_data.find('streams/stream[0]/transfers')
    if transfers_node is not None:
        carousel_count = len(transfers_node)
        carousel_status = []
        for child in transfers_node:
            has_path = get_text(child, 'path') != ''
            has_hash = get_text(child, 'hash') != ''
            status = has_path and has_hash
            carousel_status.append(status)
    else:
        carousel_count = 0
        carousel_status = []
    return (carousel_count, carousel_status)


def read_setup(setup_path):
    if not os.path.exists(setup_path):
        return {}
    try:
        with open(setup_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        syslog.syslog('Librarian setup file load failed: {}'.format(str(e)))
        return {}


def get_tuner_preset(setup_path):
    setup = read_setup(setup_path)
    ondd_setup = setup.get('ondd', {})
    preset = fingerprint_preset(ondd_setup)
    return preset


def fingerprint_preset(data):
    if not data:
        return 0
    data = {k: str(v) for k, v in data.items() if k in COMPARE_KEYS}
    for preset in PRESETS:
        preset_data = {k: v for k, v in preset[2].items() if k in COMPARE_KEYS}
        if preset_data == data:
            return preset[1]
    return 0


def collect_data(socket_path, setup_path):
    try:
        timestamp = time.time()
        syslog.syslog('Collecting data')

        # Obtain status information to get lock, PID, bitrate and service ID
        status_data = get_data(socket_path, '/status')

        # Signal data
        signal_lock = get_text(status_data, 'tuner/lock', 'no') == 'yes'

        if signal_lock:
            service_lock = get_text(
                status_data, 'streams/stream[0]/pid', None) != None
        else:
            service_lock = False

        if signal_lock:
            signal_strength = int(get_text(status_data, 'tuner/signal'))
        else:
            signal_strength = 0

        if signal_lock:
            snr = float(get_text(status_data, 'tuner/snr'))
        else:
            snr = 0

        if signal_lock:
            bitrate = int(
                get_text(status_data, 'streams/stream[0]/bitrate', 0))
        else:
            bitrate = 0

        # Service data
        #
        # The PID and service ID may remain in place regardless of lock status.
        # This is because ONDD remembers the last PID/ID it was using.

        # Obtain information about transfers
        if signal_lock:
            transfers_data = get_data(socket_path, '/transfers')
            carousel_count, carousel_status = get_carousal_data(transfers_data)
        else:
            carousel_count = 0
            carousel_status = []

        # Obtain tuner settings

        vendor, model = get_tuner_data()
        preset = get_tuner_preset(setup_path)

        time_taken = time.time() - timestamp
        syslog.syslog(
            'Finished collecting data in {} seconds'.format(time_taken))

        return {
            'signal_lock': signal_lock,
            'service_lock': service_lock,
            'signal_strength': signal_strength,
            'bitrate': bitrate,
            'snr': snr,
            'timestamp': timestamp,
            'tuner_vendor': vendor,
            'tuner_model': model,
            'tuner_preset': preset,
            'carousel_count': carousel_count,
            'carousel_status': carousel_status,
        }
    except Exception as e:
        syslog.syslog('Error while collecting data: {}'.format(e))
        return None


def get_buffer(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (OSError, IOError, ValueError):
        return []


def write_buffer(path, data):
    with open(path, 'w') as f:
        return json.dump(data, f)


def clear_buffer(path):
    try:
        os.unlink(path)
    except (OSError, IOError):
        pass


def send_or_buffer(server_url, buffer_path, data):
    # Get existing data from buffer
    all_data = get_buffer(buffer_path)
    all_data.append(data)
    if (time.time() - all_data[0]['timestamp']) > TRANSMIT_PERIOD:
        # keep and send only entries that are not older than transmit period
        all_data = [item for item in all_data
                    if time.time() - item['timestamp'] <= TRANSMIT_PERIOD]
        syslog.syslog('Transmitting buffered data')
        try:
            data_stream = to_stream_str(all_data)
            http_params = {'stream': data_stream}
            urlopen(server_url, urlencode(http_params))
        except IOError as err:
            syslog.syslog('Could not establish connection to {}: {}'.format(
                server_url, err))
        else:
            clear_buffer(buffer_path)
            syslog.syslog('Transmission complete, clearing local buffer')
            return

    write_buffer(buffer_path, all_data)


def is_activator_present(activator):
    return os.path.exists(activator)


def monitor_loop(server_url, key_path, socket_path, buffer_path, platform,
                 activator, setup_path):
    client_key = generate_key(key_path)
    try:
        while 1:
            # skip data collection and transmissions when the specified file
            # is present, and work normally otherwise. if activator is not
            # specified it should always behave normally
            if activator and not is_activator_present(activator):
                time.sleep(HEARTBEAT_PERIOD)
                continue

            data = collect_data(socket_path, setup_path)
            if data:
                data['client_id'] = client_key
                send_or_buffer(server_url, buffer_path, data)

            time.sleep(HEARTBEAT_PERIOD)
    except KeyboardInterrupt:
        syslog.syslog('Exiting due to keyboard interrupt')
        return 0
    except Exception as err:
        syslog.syslog('Abnormal exit due to error: {}'.format(err))
        return 1
    syslog.syslog('Existing normally')
    return 0


def main():
    parser = argparse.ArgumentParser('report ONDD internal state to remote '
                                     'server')
    parser.add_argument('--url', '-u', metavar='URL', help='remote server URL')
    parser.add_argument('--key', '-k', metavar='PATH', help='client ID key '
                        'file', default='/var/lib/outernet/monitor.key')
    parser.add_argument('--socket', '-s', metavar='PATH', help='path to '
                        'ONDD socket', default='/var/run/ondd.ctrl')
    parser.add_argument('--buffer', '-b', metavar='PATH', help='path to '
                        'data buffer', default='/tmp/monitor.buffer')
    parser.add_argument('--platform', '-p', metavar='NAME', help='platform '
                        'name', default=None)
    parser.add_argument('--setup', '-l', metavar='PATH', help='path to '
                        'librarian setup', default=None)
    parser.add_argument('--activator', '-a', metavar='PATH', help='path to '
                        'activation file', default=None)
    parser.add_argument('--pid', '-P', metavar='PATH', help='path to PID file',
                        default='/var/run/monitoring.pid')
    args = parser.parse_args()
    syslog.openlog(LOG_HANDLE)

    with open(args.pid, 'w') as f:
        f.write(str(os.getpid()))

    exiter = exit(args.pid)

    signal.signal(signal.SIGTERM, exiter)

    ret = monitor_loop(args.url, args.key, args.socket, args.buffer,
                       args.platform, args.activator, args.setup)

    exiter(code=ret)

if __name__ == '__main__':
    main()
