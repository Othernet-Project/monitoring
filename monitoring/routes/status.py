import datetime

from bottle import request

from ..ext.template import view


@view('status')
def show_status():
    satellites = request.app.config['sat_data']
    bitrate_threshold = request.app.config['reporting.bitrate_threshold']
    error_rate_threshold = request.app.config['reporting.error_rate_threshold']
    last_check = request.app.config.get('last_check')
    if last_check:
        last_check = datetime.datetime.fromtimestamp(int(last_check))
    else:
        last_check = None

    return dict(satellites=satellites,
                bitrate_threshold=bitrate_threshold,
                error_rate_threshold=error_rate_threshold,
                status=request.app.config.get('last_report', {}),
                last_check=last_check)


def route(config):
    return (
        (
            '/',
            'GET',
            show_status,
            'status:main',
            {}
        ),
    )
