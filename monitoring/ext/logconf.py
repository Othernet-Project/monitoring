import logging
from logging.config import dictConfig as log_config


def pre_init(config):
    log_config({
        'version': 1,
        'root': {
            'handlers': ['file'],
            'level': logging.DEBUG,
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'filename': config['logging.output'],
                'maxBytes': config['logging.size'],
                'backupCount': config['logging.backups'],
            },
        },
        'formatters': {
            'default': {
                'format': config['logging.format'],
                'datefmt': config['logging.date_format'],
            },
        },
    })
