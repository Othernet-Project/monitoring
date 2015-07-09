import time
import itertools

from ..utils.smtpclient import SMTPClient

# Interval in which client reports are checked
CHECK_INTERVAL = 5 * 60

# Minimum inteval between two consecutive notifications
NOTIFICATION_INTERVAL = 2 * 60 * 60


class FixedLengthList(list):
    """
    Stores only a fixed number of items in the list such that appending to
    the end of the list removes the first item when list reaches predefined
    length.
    """
    max_length = 3

    def append(self, item):
        while len(self) >= self.max_length:
            self.pop(0)
        super(FixedLengthList, self).append(item)


class ClientError(object):
    WARNING = 1
    CRITICAL = 2

    kind = 'unknown'
    parameter = 'unknown'
    severity = CRITICAL

    def __init__(self, client_id, country, value):
        self.timestamp = time.time()
        self.client_id = client_id
        self.country = country
        self.value = value

    def __str__(self):
        timestamp = time.strftime('%b %d %H:%M', time.gmtime(self.timestamp))
        return ('[{timestamp}] Client {client_id} from {country} '
                'reported {kind} with aggregate value '
                'of {value} {parameter}').format(
                    timestamp=timestamp,
                    client_id=self.client_id,
                    kind=self.kind,
                    value=self.value,
                    parameter=self.parameter,
                    country=self.country)


class HighErrorRate(ClientError):
    kind = 'high error rate'
    parameter = 'errors rate'
    severity = ClientError.CRITICAL


class LowBitrate(ClientError):
    kind = 'low bitrate'
    parameter = 'bps'
    severity = ClientError.WARNING


def pre_init(config):
    config['last_check'] = 0
    config['sat_data'] = dict(
        [s.split(':') for s in config['data.satellites']])


def signal_ok(row):
    if not row.bitrate:
        return False
    return row.transfers


def get_sat_reports(db):
    """ Select all records added since last check """
    time_bracket = time.time() - CHECK_INTERVAL
    # Note that we are deliberately NOT taking into account any records that do
    # not have a lock. This is intentional. If there is no lock, we can't
    # really assume anything about the signal, so it does not make sense to
    # claim unlocked signal is bad.
    qry = db.Select('*', 'stats', where=['reported >= ?', 'signal_lock = 1'],
                    order=['sat_config', 'client_id', 'timestamp'])
    db.query(qry, time_bracket)
    return db.results


def by_sat(results):
    return itertools.groupby(results, lambda r: r.sat_config)


def by_client(results):
    return itertools.groupby(results, lambda r: r.client_id)


def client_report(results):
    """ Return client report

    We calculate the client error rate by total number of errors (signal not
    OK) per total number of datapoints. We estimate that there is failure if
    more than 1/4 of datapoints are failing, and if the last 3 data points are
    failing.

    This function returns the client error rate, the average bitrate over the
    entire set, and the last status.
    """
    datapoints = 0
    total_failures = 0
    total_bitrate = 0
    last_3 = FixedLengthList()
    country = 'n/a'
    for r in results:
        ok = signal_ok(r)
        datapoints += 1
        total_failures += not ok
        total_bitrate += r.bitrate
        last_3.append(ok)
        if r.location:
            country = r.location
    error_rate = total_failures / datapoints
    avg_bitrate = total_bitrate / datapoints
    last_status = all(last_3)
    return error_rate, avg_bitrate, last_status, country


def error_block(title, errors):
    msg = ''
    msg += '{}:\n\n'.format(title)
    msg += '\n'.join([str(e) for e in errors])
    msg += '\n\n'
    return msg


def construct_message(errors):
    critical = []
    warnings = []

    for e in errors:
        if e.severity == e.CRITICAL:
            critical.append(e)
        else:
            warnings.append(e)

    msg = ''
    if critical:
        msg += error_block('CRITICAL ALERTS', critical)
    if warnings:
        msg += error_block('WARNIGNS', warnings)
    return msg


def send_reports(sat_errors, config):
    smtp_host = config['email.host']
    smtp_port = config['email.port']
    smtp_ssl = config['email.secure']
    smtp_user = config['email.username']
    smtp_pass = config['email.password']
    recipients = config['reporting.recipients']
    c = SMTPClient(smtp_host, smtp_port, smtp_ssl, smtp_user, smtp_pass)
    for sat, errors in sat_errors.items():
        sat_name = config['sat_data'].get(sat, 'Unknown bird')
        subject = '[OUTERNET MONITOR ALERT] {}'.format(sat_name)
        message = construct_message(errors)
        c.send(recipients, subject, message)


def report_hook(app):
    config = app.config

    last_check = config['last_check']

    if last_check + CHECK_INTERVAL > time.time():
        return

    task_runner = config['task.runner']
    error_threshold = config['reporting.error_rate_threshold']
    bitrate_threshold = config['reporting.bitrate_threshold']

    db = app.config['database.databases'].main
    reports = get_sat_reports(db)

    if not len(reports):
        return

    reports_by_sat = by_sat(reports)

    sat_errors = {}

    for sat_id, sat_reports in reports_by_sat:
        clients = 0
        total_error_rate = 0
        total_bitrate = 0

        errors = []

        reports_by_client = by_client(sat_reports)
        for client_id, client_reports in reports_by_client:
            clients += 1
            errate, avg_bitrate, last_status, country = client_report(
                client_reports)
            total_error_rate += errate
            total_bitrate += avg_bitrate
            if not last_status and errate > error_threshold:
                errors.append(HighErrorRate(client_id, country, errate))
            elif avg_bitrate < bitrate_threshold:
                errors.append(LowBitrate(client_id, country, avg_bitrate))

        if errors:
            sat_errors[sat_id] = errors

    if sat_errors:
        send_reports(sat_errors, config)

    app.config['last_check'] = time.time()
