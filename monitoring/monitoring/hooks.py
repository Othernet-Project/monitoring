from .reporting import send_report


def initialize(supervisor):
    config = supervisor.config

    report_interval = config['reporting.interval']
    # schedule an immediate report sending
    supervisor.exts.tasks.schedule(send_report, args=(supervisor,))

    # schedule periodic report sending
    supervisor.exts.tasks.schedule(send_report,
                                   args=(supervisor,),
                                   periodic=True,
                                   delay=report_interval)

    config['last_check'] = 0
