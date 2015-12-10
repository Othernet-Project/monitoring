COMPARE_KEYS = ('frequency', 'symbolrate', 'polarization', 'delivery',
                'modulation')

PRESETS = [
    ('Galaxy 19 (97.0W)', 1, {
        'frequency': '11929',
        'symbolrate': '22000',
        'polarization': 'v',
        'delivery': 'DVB-S',
        'modulation': 'QPSK',
    }),
    ('Hotbird 13 (13.0E)', 2, {
        'frequency': '11471',
        'symbolrate': '27500',
        'polarization': 'v',
        'delivery': 'DVB-S',
        'modulation': 'QPSK',
    }),
    ('Intelsat 20 (68.5E)', 3, {
        'frequency': '12522',
        'symbolrate': '27500',
        'polarization': 'v',
        'delivery': 'DVB-S',
        'modulation': 'QPSK',
    }),
    ('AsiaSat 5 C-band (100.5E)', 4, {
        'frequency': '3960',
        'symbolrate': '30000',
        'polarization': 'h',
        'delivery': 'DVB-S',
        'modulation': 'QPSK',
    }),
    ('Eutelsat (113.0W)', 5, {
        'frequency': '12089',
        'symbolrate': '11719',
        'polarization': 'h',
        'delivery': 'DVB-S',
        'modulation': 'QPSK',
    }),
    ('ABS-2 (74.9E)', 6, {
        'frequency': '11734',
        'symbolrate': '44000',
        'polarization': 'h',
        'delivery': 'DVB-S',
        'modulation': 'QPSK',
    }),
]

def get_sat_name(preset_id, default=''):
    for preset in PRESETS:
        if preset[1] == preset_id:
            return preset[0]
    return default


def get_preset_ids():
    return [preset[1] for preset in PRESETS]
