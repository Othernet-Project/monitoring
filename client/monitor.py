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
from urllib2 import urlopen
import xml.etree.ElementTree as ET
from contextlib import contextmanager

LOG_HANDLE = 'outernet.monitor'
ONDD_SOCKET_CONNECT_RETRIES = 3
ONDD_SOCKET_CONNECT_TIMEOUT = 5  # 5 seconds per try
ONDD_SOCKET_TIMEOUT = 20.0
ONDD_SOCKET_BUFF = 2048
ONDD_SOCKET_ENCODING = 'utf8'
HEARTBEAT_PERIOD = 60  # 1 minute
TRANSMIT_PERIOD = 5 * 60  # 5 minutes
NULL_BYTE = '\0'


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
            syslog.syslog('Could not connect to socket. '
                          'Pausing for next attempt')
            time.sleep(ONDD_SOCKET_CONNECT_TIMEOUT)
    syslog.syslog('Connected to socket')
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
    return ET.fromstring(data)


def get_text(root, xpath, default=''):
    try:
        return root.find(xpath).text
    except AttributeError:
        return default


def collect_data(socket_path):
    timestamp = time.time()
    syslog.syslog('Collecting data')

    # Obtain status information to get lock, PID, bitrate and service ID
    status_data = get_data(socket_path, '/status')

    # Signal data
    lock = get_text(status_data, 'tuner/lock', 'no') == 'yes'

    if lock:
        snr = float(get_text(status_data, 'tuner/snr'))
    else:
        snr = 0

    if lock:
        bitrate = int(get_text(status_data, 'streams/stream[0]/bitrate', 0))
    else:
        bitrate = 0

    # Service data
    #
    # The PID and service ID may remain in place regardless of lock status.
    # This is because ONDD remembers the last PID/ID it was using.
    pid = get_text(status_data, 'streams/stream[0]/pid')
    ident = get_text(status_data, 'streams/stream[0]/ident')

    # Obtain information about transfers
    if lock:
        transfers_data = get_data(socket_path, '/transfers')
        transfer = get_text(
            transfers_data, 'streams/stream[0]/transfers/transfer[0]/path')
        has_transfer = transfer != ''
    else:
        has_transfer = False

    # Obtain tuner settings
    settings_data = get_data(socket_path, '/settings')
    sat_config = sat_ident(
        get_text(settings_data, 'tuner/delivery', 'none'),
        get_text(settings_data, 'tuner/frequency', ''),
        get_text(settings_data, 'tuner/modulation', ''),
        get_text(settings_data, 'tuner/symbolrate', ''),
        get_text(settings_data, 'tuner/voltage', ''),
        get_text(settings_data, 'tuner/tone', ''),
    )

    time_taken = time.time() - timestamp
    syslog.syslog('Finished collecting data in {} seconds'.format(time_taken))

    return {
        'service_id': ident,
        'pid': pid,
        'signal_lock': lock,
        'bitrate': bitrate,
        'snr': snr,
        'transfers': has_transfer,
        'sat_config': sat_config,
        'timestamp': timestamp,
        'processing_time': time_taken,
    }


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
            urlopen(server_url, json.dumps(all_data))
        except IOError as err:
            syslog.syslog('Could not establish connection to {}: {}'.format(
                server_url, err))
        else:
            clear_buffer(buffer_path)
            syslog.syslog('Transmission complete, claring local buffer')
            return

    write_buffer(buffer_path, all_data)


def is_activator_present(activator):
    return os.path.exists(activator)


def monitor_loop(server_url, key_path, socket_path, buffer_path, platform,
                 activator):
    client_key = generate_key(key_path)
    try:
        while 1:
            # skip data collection and transmissions when the specified file
            # is present, and work normally otherwise. if activator is not
            # specified it should always behave normally
            if activator and not is_activator_present(activator):
                time.sleep(HEARTBEAT_PERIOD)
                continue

            data = collect_data(socket_path)
            data['platform'] = platform
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
                       args.platform, args.activator)

    exiter(code=ret)

if __name__ == '__main__':
    main()
