from __future__ import division


import time
import uuid

from bitarray import bitarray


ENDIAN = 'big'
MARKER = bitarray('010011110100100001000100', ENDIAN) #OHD

def _to_stream_v1(heartbeats):
    base_time = time.time()
    datagrams = []
    # Reverse iterate over the heartbeats for timestamp delta calculations
    for h in reversed(heartbeats):
        h = h.copy()
        prev_time = h['timestamp']
        h = _normalize_heartbeat_v1(h, base_time)
        datagram = _to_datagram_v1(h)
        datagrams.append(datagram)
        base_time = prev_time
    # Get back the original order
    datagrams.reverse()
    stream = bitarray()
    for d in datagrams:
        stream.extend(d)
    return stream


def _to_datagram_v1(heartbeat):
    datagram = bitarray(34 * 8) # 272 bits
    datagram.setall(False)
    datagram[0:24] = MARKER
    datagram[24:152] = to_bitarray(heartbeat['client_id'], 16)
    datagram[152:156] = to_bitarray(heartbeat['timestamp'], 1)[4:]
    datagram[156:172] = to_bitarray(heartbeat['tuner_vendor'], 2)
    datagram[172:188] = to_bitarray(heartbeat['tuner_model'], 2)
    datagram[188:193] = to_bitarray(heartbeat['tuner_preset'], 1)[3:]
    datagram[193] = heartbeat['signal_lock']
    datagram[194] = heartbeat['service_lock']
    datagram[195:199] = to_bitarray(heartbeat['signal_strength'], 1)[4:]
    datagram[199:204] = to_bitarray(heartbeat['snr'], 1)[3:]
    datagram[204:210] = to_bitarray(heartbeat['bitrate'], 1)[2:]
    datagram[210:215] = to_bitarray(heartbeat['carousel_count'], 1)[3:]
    datagram[215:246] = bitarray(heartbeat['carousel_status'])
    datagram[246:248] = False
    datagram[248:272] = MARKER
    return datagram


def _normalize_heartbeat_v1(heartbeat, base_time):
    # Get the device id as an int
    heartbeat['client_id'] = uuid.UUID(heartbeat['client_id'], version=4).int

    # Convert vendor id from hex string to int
    heartbeat['tuner_vendor'] = int(heartbeat['tuner_vendor'], 16)

    # Convert model id from hex string to int
    heartbeat['tuner_model'] = int(heartbeat['tuner_model'], 16)

    # Scale strength in the range of 0-10
    heartbeat['signal_strength'] = clamp_max(int(heartbeat['signal_strength'] / 10), 10)

    # Scale SNR to the range of 0-31
    heartbeat['snr'] = clamp_max(int(heartbeat['snr'] * 10), 31)

    # Convert bitrate to increments of 10 Kbps and clamp it to 63
    bitrate = int(heartbeat['bitrate'] / (1000 * 10))
    heartbeat['bitrate'] = clamp_max(bitrate, 63)

    # Calculate timestamp relative to the previous heartbeat's timestamp
    # and then reduce it to 5-second resolution
    timestamp = clamp_max(int((base_time - heartbeat['timestamp']) / 5), 127)
    heartbeat['timestamp'] = timestamp
    return heartbeat


def _from_stream_v1(stream):
    heartbeats = []
    base_time = time.time()
    marker_positions = stream.search(MARKER)
    # Reverse iterate over datagrams in stream because of timestamp deltas
    marker_positions.reverse()
    i = 0
    while i < len(marker_positions) - 1:
        end = marker_positions[i]
        start = marker_positions[i + 1]
        i += 2
        heartbeat = _from_datagram_v1(stream[start:end])
        heartbeat = _denormalize_heartbeat_v1(heartbeat, base_time)
        heartbeats.append(heartbeat)
        base_time = heartbeat['timestamp']
    # Get original order
    heartbeats.reverse()
    return heartbeats


def _from_datagram_v1(datagram):
    heartbeat = dict()
    heartbeat['client_id'] = str(uuid.UUID(bytes=datagram[24:152].tobytes()))
    heartbeat['timestamp'] = from_bitarray(datagram[152:156])
    heartbeat['tuner_vendor'] = from_bitarray(datagram[156:172])
    heartbeat['tuner_model'] = from_bitarray(datagram[172:188])
    heartbeat['tuner_preset'] = from_bitarray(datagram[188:193])
    heartbeat['signal_lock'] = datagram[193]
    heartbeat['service_lock'] = datagram[194]
    heartbeat['signal_strength'] = from_bitarray(datagram[195:199])
    heartbeat['snr'] = from_bitarray(datagram[199:204])
    heartbeat['bitrate'] = from_bitarray(datagram[204:210])
    count = from_bitarray(datagram[210:215])
    heartbeat['carousel_count'] = count
    heartbeat['carousel_status'] = datagram[215:215+count].tolist()
    return heartbeat


def _denormalize_heartbeat_v1(heartbeat, base_time):
    # Regain original timestamp (5-second resolution)
    heartbeat['timestamp'] = base_time - (heartbeat['timestamp'] * 5)

    # Convert id from int to hex
    heartbeat['tuner_vendor'] = id_hex(heartbeat['tuner_vendor'])

    # Convert id from int to hex
    heartbeat['tuner_model'] = id_hex(heartbeat['tuner_model'])

    # Regain original strength by scaling to 10
    heartbeat['signal_strength'] = heartbeat['signal_strength'] * 10

    # Downscale signal-noise ratio by 10 to original value
    heartbeat['snr'] = heartbeat['snr'] / 10

    # Rescale bitrate from increments of 10 Kbps to bps
    heartbeat['bitrate'] = int(heartbeat['bitrate'] * (1000 * 10))

    return heartbeat


SERIALIZER_MAPPING = (
    (1, _to_stream_v1),
)

DESERIALIZER_MAPPING = (
    (1, _from_stream_v1),
)


def to_stream_str(heartbeats, version):
    return to_stream(heartbeats, version).tobytes()


def to_stream(heartbeats, version):
    for v, fn in SERIALIZER_MAPPING:
        if v == version:
            return fn(heartbeats)
    raise ValueError('Invalid serialization version {}'.format(version))


def from_stream_str(stream, version):
    ba = bitarray()
    ba.frombytes(bytes(stream))
    return from_stream(ba, version)


def from_stream(stream, version):
    for v, fn in DESERIALIZER_MAPPING:
        if v == version:
            return fn(stream)
    raise ValueError('Invalid deserialization version {}'.format(version))


def get_stream_version(stream):
    version = from_bitarray(stream[24:40])
    return version


def clamp_max(val, maxval):
    return clamp(val, 0, maxval)


def clamp(val, minval, maxval):
    return max(minval, min(val, maxval))


def id_hex(id, length=4):
    return (hex(id)[2:]).zfill(length)


def to_bitarray(n, length):
    b = bitarray()
    b.frombytes(to_bytes(n, length))
    return b


def from_bitarray(b):
    while b.length() % 8 != 0:
        b.insert(0, False)
    return from_bytes(b.tobytes())


def to_bytes(n, length):
    h = '%x' % n
    s = ('0'*(len(h) % 2) + h).zfill(length*2).decode('hex')
    return s


def from_bytes(b):
    return int(b.encode('hex'), 16)
