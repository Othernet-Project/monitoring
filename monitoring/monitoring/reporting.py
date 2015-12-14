import time
import logging
import itertools

from ..utils.smtpclient import SMTPClient
from ..core.satdata import get_sat_name, get_preset_ids


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

    def __init__(self, client_id, value):
        self.timestamp = time.time()
        self.client_id = client_id
        self.value = value

    def __str__(self):
        timestamp = time.strftime('%b %d %H:%M', time.gmtime(self.timestamp))
        return ('[{timestamp}] Client {client_id} '
                'reported {kind} with aggregate value '
                'of {value} {parameter}').format(
                    timestamp=timestamp,
                    client_id=self.client_id,
                    kind=self.kind,
                    value=self.value,
                    parameter=self.parameter)


class HighErrorRate(ClientError):
    kind = 'high error rate'
    parameter = 'errors rate'
    severity = ClientError.CRITICAL


class LowBitrate(ClientError):
    kind = 'low bitrate'
    parameter = 'bps'
    severity = ClientError.WARNING


def signal_ok(row):
    return row['service_ok']


def get_sat_reports(db):
    """ Select all records added since last check """
    time_bracket = time.time() - CHECK_INTERVAL
    # Note that we are deliberately NOT taking into account any records that do
    # not have a lock. This is intentional. If there is no lock, we can't
    # really assume anything about the signal, so it does not make sense to
    # claim unlocked signal is bad.
    qry = db.Select('*', 'stats', where=['reported >= %(reported)s', 'signal_lock = True'],
                    order=['tuner_preset', 'client_id', 'timestamp'])
    return db.fetchall(qry, { 'reported': time_bracket })


def by_sat(results):
    return itertools.groupby(results, lambda r: r['tuner_preset'])


def by_client(results):
    return itertools.groupby(results, lambda r: r['client_id'])


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
    for r in results:
        ok = signal_ok(r)
        datapoints += 1
        total_failures += not ok
        total_bitrate += r['bitrate']
        last_3.append(ok)
    error_rate = total_failures / datapoints
    avg_bitrate = total_bitrate / datapoints
    last_status = all(last_3)
    return error_rate, avg_bitrate, last_status


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
    if not critical and not warnings:
        msg += 'OPERATIONAL AGAIN.\n\n'
    return msg


def get_state(errors):
    if any([e.severity == e.CRITICAL for e in errors]):
        return 'CRITICAL'
    if any([e.severity == e.WARNING for e in errors]):
        return 'WARNING'
    return 'OPERATIONAL'


def get_changed_states(sat_errors, config):
    default = dict((p, 'OPERATIONAL') for p in get_preset_ids())
    old_state = config.get('last_state', default)
    # prepare current state of sat_id:status pairs
    state = dict((p, get_state(sat_errors.get(p, [])))
                 for p in get_preset_ids())
    # find difference between current and previous state
    changes = dict(set(old_state.items()).difference(state.items()))
    config['last_state'] = state
    # return changed sat_id:errors pairs (empty error list if it works again)
    return dict((key, sat_errors.get(key, [])) for key in changes)


def send_reports(sat_errors, config):
    smtp_host = config['email.host']
    smtp_port = config['email.port']
    smtp_ssl = config['email.secure']
    smtp_user = config['email.username']
    smtp_pass = config['email.password']
    recipients = config['reporting.recipients']
    c = SMTPClient(smtp_host, smtp_port, smtp_ssl, smtp_user, smtp_pass)
    for preset, errors in sat_errors.items():
        sat_name = get_sat_name(preset)
        subject = '[OUTERNET MONITOR ALERT] {}'.format(sat_name)
        message = construct_message(errors)
        try:
            c.send(recipients, subject, message)
        except Exception:
            logging.exception("Mail report sending failed.")


def aggregate_status(sat_status):
    aggregate = {}
    for sat_name, data in sat_status.items():
        nconfigs = len(data)
        nclients = sum([d['clients'] for d in data]) or 1
        all_errors = list(itertools.chain(*[d['errors'] for d in data]))

        fcritical = sum([e.severity == e.CRITICAL for e in all_errors]) \
            / nclients
        fwarnings = sum([e.severity == e.WARNING for e in all_errors]) \
            / nclients
        if fcritical > 0.1:
            status = 'CRITICAL'
        elif fwarnings > 0.1:
            status = 'WARNINGS'
        else:
            status = 'NORMAL'

        aggregate[sat_name] = {
            'status': status,
            'clients': nclients,
            'error_rate': sum([d['error_rate'] for d in data]) / nconfigs,
            'bitrate': sum([d['bitrate'] for d in data]) / nconfigs
        }

    return aggregate


def send_report(supervisor):
    app = supervisor.app
    config = app.config

    last_check = config['last_check']

    if last_check + CHECK_INTERVAL > time.time():
        return

    error_threshold = config['reporting.error_rate_threshold']
    bitrate_threshold = config['reporting.bitrate_threshold']

    db = supervisor.exts.databases['monitoring']
    reports = get_sat_reports(db)

    reports_by_sat = by_sat(reports)

    sat_errors = {}
    sat_status = {}

    for tuner_preset, sat_reports in reports_by_sat:

        clients = 0
        total_error_rate = 0
        total_bitrate = 0

        errors = []

        reports_by_client = by_client(sat_reports)
        for client_id, client_reports in reports_by_client:
            clients += 1
            errate, avg_bitrate, last_status = client_report(client_reports)
            total_error_rate += errate
            total_bitrate += avg_bitrate
            if not last_status and errate > error_threshold:
                errors.append(HighErrorRate(client_id, errate))
            #elif avg_bitrate < bitrate_threshold:
            #    errors.append(LowBitrate(client_id, avg_bitrate))

        sat_name = get_sat_name(tuner_preset)
        #sat_data.get(sat_id, 'Unknown')
        sat_status.setdefault(sat_name, [])
        sat_status[sat_name].append({
            'errors': errors,
            'error_rate': total_error_rate / (clients or 1),
            'bitrate': total_bitrate / (clients or 1),
            'clients': clients})

        if errors:
            sat_errors[tuner_preset] = errors
            #sat_errors[sat_id] = errors

    changes = get_changed_states(sat_errors, config)
    if changes:
        send_reports(changes, config)

    config['last_report'] = aggregate_status(sat_status)
    config['last_check'] = time.time()
