import time
import itertools

CHECK_INTERVAL = 5 * 60


def pre_init(config):
    config['last_check'] = 0
    config['sat_data'] = dict(
        [s.split(':') for s in config['data.satellites']])


def get_sat_reports(db):
    time_bracket = time.time() - CHECK_INTERVAL
    qry = db.Select('*', 'stats', where='reported >= ?',
                    order=['sat_config', 'client_id', 'timestamp'])
    db.query(qry, time_bracket)
    return db.results


def by_sat(results):
    return itertools.groupby(results, lambda r: r.sat_config)


def by_client(results):
    return itertools.groupby(results, lambda r: r.client_id)


def report_hook(app):
    config = app.config

    last_check = config['last_check']

    if last_check + CHECK_INTERVAL > time.time():
        return

    sat_data = config['sat_data']

    db = app.config['database.databases'].main
    reports = get_sat_reports(db)
    if not len(reports):
        print("Nothing to report")
    reports_by_sat = by_sat(reports)
    for sat_id, sat_report in reports_by_sat:
        print('Results for sat id: {} ({})'.format(
            sat_id, sat_data.get(sat_id)))
        reports_by_client = by_client(reports)
        for client_id, client_reports in reports_by_client:
            print('Results for client id: {}'.format(client_id))
            print(list(client_reports))
    app.config['last_check'] = time.time()
