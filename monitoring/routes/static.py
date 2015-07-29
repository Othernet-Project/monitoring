import datetime

from bottle import request, static_file


EXP_TIMESTAMP = '%a, %d %b %Y %H:%M:%S GMT'


def serve_static(path):
    response = static_file(path, root=request.assets.directory)
    exp = datetime.datetime.utcnow() + datetime.timedelta(365)
    response.headers['Expires'] = exp.strftime(EXP_TIMESTAMP)
    return response


def route(config):
    url = config['assets.url']
    return (
        ('{}<path:path>'.format(url), 'GET', serve_static, 'static',
         {'skip': ['sessions']}),
    )
