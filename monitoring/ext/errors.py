from .template import view


@view('403')
def error403(*args, **kwargs):
    return dict()


@view('404')
def error404(*args, **kwargs):
    return dict()


@view('500')
def error500(*args, **kwargs):
    return dict()


def pre_init(config):
    app = config['bottle']
    app.error(403)(error403)
    app.error(404)(error404)
    app.error(500)(error500)
