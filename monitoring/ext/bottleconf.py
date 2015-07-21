import os

import bottle

import bottle_utils.html


def pre_init(config):
    app = config['bottle']
    bottle.debug(config['server.debug'])
    bottle.TEMPLATE_PATH.insert(0, os.path.join(
        config['root'], config['app.view_path']))
    bottle.BaseTemplate.defaults.update({
        'request': bottle.request,
        'h': bottle_utils.html,
        'url': app.get_url,
        'sat_ids': {s.split(':')[0]: s.split(':')[1]
                    for s in config['data.satellites']},
        'REDIRECT_DELAY': config['app.redirect_delay'],
        '_': lambda x: x,
    })
