from .reporting import send_report


def initialize(supervisor):
    config = supervisor.config
    # schedule periodic report sending
    report_interval = config['reporting.interval']
    supervisor.exts.tasks.schedule(send_report,
                                   args=(supervisor,),
                                   periodic=True,
                                   delay=report_interval)

    config['last_check'] = 0
