import datetime

from bottle import request

from librarian_core.contrib.templates.renderer import view

from ...core.satdata import get_sat_name, get_preset_ids


@view('status')
def show_status():
    bitrate_threshold = request.app.config['reporting.bitrate_threshold']
    error_rate_threshold = request.app.config['reporting.error_rate_threshold']
    last_check = request.app.config.get('last_check')
    if last_check:
        last_check = datetime.datetime.fromtimestamp(int(last_check))
    else:
        last_check = None

    satellites = sorted(set([get_sat_name(pid) for pid in get_preset_ids()]))

    return dict(satellites=satellites,
                bitrate_threshold=bitrate_threshold,
                error_rate_threshold=error_rate_threshold,
                status=request.app.config.get('last_report', {}),
                last_check=last_check)   # fetch report from database and return status page
