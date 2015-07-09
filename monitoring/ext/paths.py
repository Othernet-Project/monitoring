import os
import logging


def ensure_dir(path):
    if os.path.exists(path):
        return
    os.makedirs(path)


def pre_init(conf):
    logging.info('Preparing application directories')
    paths = (
        conf['database.path'],
        conf['mako.module_directory'],
        conf['reporting.alert_dir'],
    )
    for p in paths:
        ensure_dir(p)
