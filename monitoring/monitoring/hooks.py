import GeoIP

from .reporting import send_report


def initialize(supervisor):
    # setup geoip as an extension
    data_path = supervisor.config['data.geoip']
    supervisor.exts.geoip = GeoIP.open(data_path, GeoIP.GEOIP_MEMORY_CACHE)
    # schedule periodic report sending
    report_interval = supervisor.config['reporting.interval']
    supervisor.exts.tasks.schedule(send_report,
                                   args=(supervisor,),
                                   periodic=True,
                                   delay=report_interval)
