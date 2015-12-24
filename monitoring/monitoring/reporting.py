from __future__ import division

import time
import logging
import itertools

from ..utils.smtpclient import SMTPClient
from ..core.satdata import get_sat_name, get_preset_ids


# Default interval for which datapoints are used
DATAPOINTS_INTERVAL = 20 * 60

# Minimum inteval between two consecutive notifications
NOTIFICATION_INTERVAL = 2 * 60 * 60

# Interval for which faulty signal from client is considered ok
SIGNAL_OK_INTERVAL = 20 * 60

# Statuses used for email alerts and dashboard
STATUS_NORMAL = 'NORMAL'
STATUS_WARNING = 'WARNING'
STATUS_CRITICAL = 'CRITICAL'


class ClientError(object):
    WARNING = 1
    CRITICAL = 2

    kind = 'unknown'
    parameter = 'unknown'
    severity = CRITICAL

    def __init__(self, client_id, health, value):
        self.timestamp = time.time()
        self.client_id = client_id
        self.health = health
        self.value = value

    def __str__(self):
        timestamp = time.strftime('%b %d %H:%M', time.gmtime(self.timestamp))
        return ('[{timestamp}] Client {client_id} '
                'reported {kind} with aggregate value '
                'of {value} {parameter} and health {health}').format(
                    timestamp=timestamp,
                    client_id=self.client_id,
                    kind=self.kind,
                    value=self.value,
                    parameter=self.parameter,
                    health=self.health)


class HighErrorRate(ClientError):
    kind = 'high error rate'
    parameter = 'errors rate'
    severity = ClientError.CRITICAL


class LowBitrate(ClientError):
    kind = 'low bitrate'
    parameter = 'bps'
    severity = ClientError.WARNING


def get_sat_reports(db, interval=DATAPOINTS_INTERVAL):
    """ Select all records added since last check """
    time_bracket = time.time() - interval
    # Note that we are deliberately NOT taking into account any records that do
    # not have a lock. This is intentional. If there is no lock, we can't
    # really assume anything about the signal, so it does not make sense to
    # claim unlocked signal is bad.
    qry = db.Select('*', 'stats', where=['reported >= %(reported)s', 'signal_lock = True'],
                    order=['tuner_preset', 'client_id', 'timestamp'])
    return db.fetchall(qry, {'reported': time_bracket})


def by_sat(results):
    return itertools.groupby(results, lambda r: r['tuner_preset'])


def by_client(results):
    return itertools.groupby(results, lambda r: r['client_id'])


def check_ok(datapoints):
    """
    Check if a client's state is ok, i.e., it has a healthy transfer profile

    We consider a datapoint to show failure if it shows no carousels or if
    none of them are receiving data. A client is said to be in a healthy
    state `HEALTH_OK` only if more than 80% of datapoints do not have failures
    """

    failures_count = 0
    datapoints_count = 0
    for d in datapoints:
        datapoints_count += 1
        if d['carousels_count'] > 0 and any(d['carousels_status']):
            continue
        failures_count += 1
    failure_rate = failures_count / (datapoints_count or 1)
    valid = (failure_rate <= 0.2) if datapoints_count else False
    return failure_rate, valid


def check_no_carousels(datapoints):
    """
    Detect if client shows history of having a valid bitrate, but no carousels
    or none of them are receiving data.

    A datapoint shows failure if it has a bitrate greater than 0, but shows
    no carousels or none of them are receiving data. If more than 80% of
    datapoints show failures, then the client is said to be at
    `HEALTH_NO_CAROUSELS` state.
    """

    datapoints_count = 0
    failures_count = 0
    # Only look at the last 10 minutes worth of data to ensure that older
    # datapoints do not incorrectly influence the failure rate calculation
    datapoints = itertools.ifilter(lambda d: (
        time.time() - d['timestamp']) <= 600, datapoints)
    for d in datapoints:
        datapoints_count += 1
        carousels_count = d['carousels_count']
        carousels_status = d['carousels_status']
        bitrate = d['bitrate']
        if bitrate > 0 and (carousels_count == 0 or not any(carousels_status)):
            failures_count += 1
    failure_rate = failures_count / (datapoints_count or 1)
    valid = (failure_rate > 0.8) if datapoints_count else False
    return failure_rate, valid


def check_bad_bitrate(datapoints):
    """
    Detect if client shows history of invalid bitrate of `0`.

    A datapoint shows failure if it has a bitrate == 0. If more than 80% of
    datapoints show failures, then the client is said to be at
    `HEALTH_BAD_BITRATE` state.
    """

    datapoints_count = 0
    failures_count = 0
    for d in datapoints:
        datapoints_count += 1
        bitrate = d['bitrate']
        if bitrate == 0:
            failures_count += 1
    failure_rate = failures_count / (datapoints_count or 1)
    valid = (failure_rate > 0.8) if datapoints_count else False
    return failure_rate, valid


def check_no_service_lock(datapoints):
    """
    Detect if client shows history of not being able to get a service lock.

    A datapoint shows failure if it has no service lock. If more than 50% of
    datapoints show failures, then the client is said to be at
    `HEALTH_NO_SERVICE_LOCK` state.
    """

    failures_count = 0
    datapoints_count = 0
    # Only look at the last 10 minutes worth of data to ensure that older
    # datapoints do not incorrectly influence the failure rate calculation
    datapoints = itertools.ifilter(lambda d:(
        time.time() - d['timestamp'] <= 600), datapoints)
    for d in datapoints:
        datapoints_count += 1
        if not d['service_lock']:
            failures_count += 1
    failure_rate = failures_count / (datapoints_count or 1)
    valid = (failure_rate >= 0.5) if datapoints_count else False
    return failure_rate, valid


def check_no_signal_lock(datapoints):
    """
    Detect if client shows history of not being able to get a signal lock.

    A datapoint shows failure if it has no signal lock. If more than 20% of
    datapoints show failures, then the client is said to be at
    `HEALTH_NO_SIGNAL_LOCK` state.
    """

    failures_count = 0
    datapoints_count = 0
    # Only look at the last 10 minutes worth of data to ensure that older
    # datapoints do not incorrectly influence the failure rate calculation
    datapoints = filter(lambda d:(time.time() - d['timestamp'] <= 600), datapoints)
    failures = filter(lambda d: not d['signal_lock'], datapoints)
    datapoints_count = len(datapoints)
    failures_count = len(failures)
    failure_rate = failures_count / (datapoints_count or 1)
    valid = (failure_rate >= 0.2) if datapoints_count else False
    return failure_rate, valid


HEALTH_OK = 'ok'
HEALTH_NO_CAROUSELS = 'no_carousels'
HEALTH_BAD_BITRATE = 'bad_bitrate'
HEALTH_NO_SERVICE_LOCK = 'no_service_lock'
HEALTH_NO_SIGNAL_LOCK = 'no_signal_lock'
HEALTH_UNKNOWN = 'unknown'


health_transition_map = {
    HEALTH_OK: (check_ok, HEALTH_NO_CAROUSELS),
    HEALTH_NO_CAROUSELS: (check_no_carousels, HEALTH_BAD_BITRATE),
    HEALTH_BAD_BITRATE: (check_bad_bitrate, HEALTH_NO_SERVICE_LOCK),
    HEALTH_NO_SERVICE_LOCK: (check_no_service_lock, HEALTH_UNKNOWN),
}


def client_report(results):
    """ Return client report

    We calculate the client error rate by total number of errors (signal not
    OK) per total number of datapoints. We estimate that there is failure if
    more than 1/4 of datapoints are failing, and if the last 3 data points are
    failing.

    This function returns the client error rate, the average bitrate over the
    entire set, and the last status.
    """
    error_rate, health = (0.0, HEALTH_OK)
    results = list(results)

    while health != HEALTH_UNKNOWN:
        transition_fn, next_state = health_transition_map[health]
        error_rate, valid_state = transition_fn(results)
        if not valid_state:
            health = next_state
        else:
            break

    datapoints_count = len(results)
    total_bitrate = sum([r['bitrate'] for r in results])
    total_errors = len(filter(lambda r: not r['service_ok'], results))

    avg_bitrate = total_bitrate / (datapoints_count or 1)
    if health == HEALTH_OK:
        status = True
    elif health == HEALTH_UNKNOWN:
        error_rate = total_errors / (datapoints_count or 1)
        status = (error_rate < 0.5)
    else:
        status = False
    return health, error_rate, avg_bitrate, status


def error_block(title, errors):
    msg = ''
    msg += '{}:\n\n'.format(title)
    msg += '\n'.join([str(e) for e in errors])
    msg += '\n\n'
    return msg


def construct_message(sat_status):
    criticals = []
    warnings = []

    for e in sat_status.get('errors', []):
        if e.severity == e.CRITICAL:
            criticals.append(e)
        else:
            warnings.append(e)

    msg = ''
    msg += 'SATELLITE STATUS: {}\n\n'.format(sat_status['alert_status'])

    if criticals:
        msg += error_block('CRITICAL ALERTS', criticals)
    if warnings:
        msg += error_block('WARNINGS', warnings)
    return msg


def get_state(sat_status):
    if sat_status:
        error_rate = sat_status['error_rate']
        if error_rate > 0.1:
            return STATUS_CRITICAL
        elif error_rate > 0.05:
            return STATUS_WARNING
        else:
            return STATUS_NORMAL
    return STATUS_NORMAL


def get_changed_states(sat_errors, config):
    default = dict((p, STATUS_NORMAL) for p in get_preset_ids())
    old_state = config.get('last_state', default)
    # prepare current state of sat_id:status pairs
    state = dict((p, get_state(sat_errors.get(p, None)))
                 for p in get_preset_ids())
    # find difference between current and previous state
    changes = dict(set(old_state.items()).difference(state.items()))
    config['last_state'] = state
    # return changed sat_id:errors pairs (empty error list if it works again)
    changed_states = dict((key, sat_errors.get(key, {})) for key in changes)
    for preset in changes:
        changed_states[preset]['alert_status'] = state.get(preset, STATUS_NORMAL)
    return changed_states


def send_reports(sat_errors, config):
    smtp_host = config['email.host']
    smtp_port = config['email.port']
    smtp_ssl = config['email.secure']
    smtp_user = config['email.username']
    smtp_pass = config['email.password']
    recipients = config['reporting.recipients']
    c = SMTPClient(smtp_host, smtp_port, smtp_ssl, smtp_user, smtp_pass)
    for preset, sat_status in sat_errors.items():
        sat_name = get_sat_name(preset)
        subject = '[OUTERNET MONITOR ALERT] {}'.format(sat_name)
        message = construct_message(sat_status)
        try:
            c.send(recipients, subject, message)
        except Exception:
            logging.exception("Mail report sending failed.")


def aggregate_status(sat_status, sat_states):
    aggregate = {}
    for sat_name, data in sat_status.items():
        status = sat_states.get(data['preset'], STATUS_NORMAL)
        aggregate[sat_name] = {
            'status': status,
            'clients': data['nclients'],
            'error_rate': data['error_rate'],
            'bitrate': data['bitrate']
        }

    return aggregate


def send_report(supervisor):
    app = supervisor.app
    config = app.config

    datapoints_interval = config['reporting.datapoints_interval']

    db = supervisor.exts.databases['monitoring']
    reports = get_sat_reports(db, datapoints_interval)

    reports_by_sat = by_sat(reports)

    sat_errors = {}
    sat_status = {}

    for tuner_preset, sat_reports in reports_by_sat:

        clients = 0
        total_bitrate = 0

        errors = []

        reports_by_client = by_client(sat_reports)
        receiving_clients = 0
        for client_id, client_reports in reports_by_client:
            clients += 1
            health, errate, avg_bitrate, status = client_report(client_reports)
            if avg_bitrate > 0.0:
                total_bitrate += avg_bitrate
                receiving_clients += 1
            if not status:
                errors.append(HighErrorRate(client_id, health, errate))

        sat_name = get_sat_name(tuner_preset)
        sat_error_rate = len(errors) / (clients or 1)
        sat_status.setdefault(sat_name, {})
        sat_status[sat_name] = {
            'preset': tuner_preset,
            'error_rate': sat_error_rate,
            'bitrate': total_bitrate / (receiving_clients or 1),
            'nclients': clients,
            'errors': errors
        }

        if errors:
            sat_errors[tuner_preset] = sat_status[sat_name]

    changes = get_changed_states(sat_errors, config)
    if changes:
        send_reports(changes, config)

    config['last_report'] = aggregate_status(sat_status, config['last_state'])
    config['last_check'] = time.time()
