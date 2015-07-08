"""
tasks.py: Execute tasks that were queued up

Copyright 2014-2015, Outernet Inc.
Some rights reserved.

This software is free software licensed under the terms of GPLv3. See COPYING
file that comes with the source code, or http://www.gnu.org/licenses/gpl.txt.
"""

import logging
import Queue


class TaskRunner(object):

    def __init__(self):
        self.task_queue = Queue.Queue()

    def schedule(self, func, *args, **kwargs):
        self.task_queue.put((func, args, kwargs))

    def execute_all(self):
        while True:
            try:
                task = self.task_queue.get(block=False)
            except Queue.Empty:
                return
            else:
                (func, args, kwargs) = task
                try:
                    func(*args, **kwargs)
                except Exception:
                    logging.exception("Background task execution failed.")


def pre_init(config):
    config['task.runner'] = TaskRunner()


def execute_tasks(app):
    task_runner = app.config['task.runner']
    task_runner.execute_all()
