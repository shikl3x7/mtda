# ---------------------------------------------------------------------------
# Remote console support for MTDA
# ---------------------------------------------------------------------------
#
# This software is a part of MTDA.
# Copyright (C) 2023 Siemens Digital Industries Software
#
# ---------------------------------------------------------------------------
# SPDX-License-Identifier: MIT
# ---------------------------------------------------------------------------

# Local imports
from mtda.console.output import ConsoleOutput
import mtda.constants as CONSTS

# System imports
import zmq
import redis

class RemoteConsole(ConsoleOutput):

    def __init__(self, host, port, screen):
        ConsoleOutput.__init__(self, screen)
        self.context = None
        self.host = host
        self.port = port
        self.socket = None
        self.topic = CONSTS.CHANNEL.CONSOLE

    def connect(self):
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket_redis = redis.Redis(host=self.host, port=6379, db=0)
        socket_redis_pubsub = socket_redis.pubsub()
        socket_redis_pubsub.subscribe(self.topic)
        socket.connect("tcp://%s:%s" % (self.host, self.port))
        socket.setsockopt(zmq.SUBSCRIBE, self.topic)
        self.context = context
        self.socket = socket
        self.socket_redis_pubsub = socket_redis_pubsub
        return socket,socket_redis_pubsub

    def dispatch(self, topic, data):
        self.write(data)

    def reader(self):
        socket,socket_redis_pubsub = self.connect()
        try:
            while self.exiting is False:
                for message in socket_redis_pubsub.listen():
                    if message['type'] == 'message':
                        self.dispatch(message['channel'],message['data'])
                #topic, data = socket.recv_multipart()
                #self.dispatch(topic, data)
        except zmq.error.ContextTerminated:
            self.socket = None

    def stop(self):
        super().stop()
        if self.context is not None:
            self.context.term()
            self.context = None


class RemoteMonitor(RemoteConsole):

    def __init__(self, host, port, screen):
        super().__init__(host, port, screen)
        self.topic = CONSTS.CHANNEL.MONITOR

    def connect(self):
        socket,socket_redis_pubsub = super().connect()
        socket.setsockopt(zmq.SUBSCRIBE, CONSTS.CHANNEL.EVENTS)
        return socket,socket_redis_pubsub

    def dispatch(self, topic, data):
        if topic != CONSTS.CHANNEL.EVENTS:
            self.write(data)
        else:
            self.on_event(data.decode("utf-8"))
