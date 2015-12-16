from .reporting import send_report


def initialize(supervisor):
    config = supervisor.config
    # schedule periodic report sending
    supervisor.exts.tasks.schedule(send_report,
                                   args=(supervisor,),
                                   periodic=True)

    config['last_check'] = 0
