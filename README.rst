====================================
ONDD state monitor server and client
====================================

This project contains a server and client for monitoring ONDD internal state.
The primary purpose of the motnioring is to detect interruptions in service.

Server
======

The server is found in the ``monitoring`` package. It is a relatively standard
bottle_ application. The server has two endpoints. The root path renders a
report based on collected data. The ``/heartbeat/`` endpoint accepts POST
requests containing the JSON payload from the client script (refer to `Client
script`_ section for the type of data collected).

Client script
=============

The ``client`` directory contains a ``monitor.py``. This script is used for
sending ONDD motniroing information. It uses the `ONDD IPC calls`_ to retrieve
the infomation. It does not send any usage information.

Data sent out to the monitoring server includes:

- signal lock
- signal quality
- service identifier
- PID
- bitrate
- presence of ongoing transfers
- timestamp of the data collection
- total time taken to collect the data

.. _bottle: http://bottlepy.org/
.. _ONDD IPC calls: https://wiki.outernet.is/wiki/ONDD_IPC
