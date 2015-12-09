from .collect import collect_heartbeat
from .status import show_status


EXPORTS = {
    'routes': {'required_by': ['librarian_core.contrib.system.routes.routes']}
}


def routes(config):
    return (
        (
            'api:heartbeat',
            collect_heartbeat,
            'POST',
            '/heartbeat/',
            {}
        ), (
            'status:main',
            show_status,
            'GET',
            '/',
            {}
        ),
    )
