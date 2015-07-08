import os
import time
import logging
import importlib

from bottle import Bottle
from gevent import pywsgi

from .confloader import ConfDict
from .signal_handlers import on_interrupt


class Application:
    LOOP_INTERVAL = 5  # in seconds

    def __init__(self, config, args, root):
        self.server = None
        self.background_hooks = []
        self.stop_hooks = []
        self.app = Bottle()
        self.root = root

        # Configure the applicaton
        self.configure(config)
        self.config['root'] = root
        self.config['bottle'] = self.app
        self.config['args'] = args

        # Register application hooks
        self.pre_init(self.config['stack.pre_init'])
        self.add_plugins(self.config['stack.plugins'])
        self.add_routes(self.config['stack.routes'])
        self.add_background(self.config['stack.background'])
        self.add_stop_hooks(self.config['stack.post_stop'])

        # Register interrupt handler
        on_interrupt(self.halt)

    def configure(self, path):
        path = os.path.abspath(path)
        base_path = os.path.dirname(path)
        self.config = ConfDict.from_file(path,
                                         base_dir=base_path,
                                         catchall=True,
                                         autojson=True)
        self.app.config = self.config

    def pre_init(self, pre_init):
        for hook in pre_init:
            hook = self._import(hook)
            hook(self.config)

    def add_plugins(self, plugins):
        for plugin in plugins:
            plugin = self._import(plugin)
            self.app.install(plugin(self.config))

    def add_routes(self, routing):
        for route in routing:
            route = self._import(route)
            for r in route(self.config):
                path, method, cb, name, kw = r
                self.app.route(path, method, cb, name=name, **kw)

    def add_background(self, background_calls):
        for hook in background_calls:
            hook = self._import(hook)
            self.background_hooks.append(hook)

    def add_stop_hooks(self, pre_stop):
        for hook in pre_stop:
            hook = self._import(hook)
            self.stop_hooks.append(hook)

    def start(self):
        host = self.config['server.bind']
        port = self.config['server.port']
        self.server = pywsgi.WSGIServer((host, port), self.app, log=None)
        self.server.start()  # non-blocking
        assert self.server.started, 'Expected server to be running'
        logging.debug("Started server on http://%s:%s/", host, port)
        if self.config['server.debug']:
            print('Started server on http://%s:%s/' % (host, port))
        self.init_background()

    def init_background(self):
        while True:
            time.sleep(self.LOOP_INTERVAL)
            for hook in self.background_hooks:
                hook(self.app)

    def halt(self):
        logging.info('Stopping the application')
        self.server.stop(5)
        logging.info('Running pre-stop hooks')
        for hook in self.stop_hooks:
            hook()

    @staticmethod
    def _import(name):
        mod, obj = name.rsplit('.', 1)
        mod = importlib.import_module(mod)
        return getattr(mod, obj)
