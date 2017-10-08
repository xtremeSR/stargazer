#! python

import pdb

import random
import re as regex
import json
import time
from multiprocessing import Pipe, Process, freeze_support
# import psutil
import argparse
import sys
import os

import tornado
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

from .utils import *
from .Battle import Battle
from .Player import Player
from .Pokemon import Pokemon
from .Agent import Agent
'''
    File: ShowdownClient.py
    Description: ShowdownClient represents the Websocket client for connecting
    to, parsing messages from, sending responses to the server.
'''

DELIM = '|'
MSG_HEAD = '>'


class ShowdownClient:
    # This class uses multiprocessing and IPC
    # to map on server messages to a process pool.
    #
    # This architecture was chosen for multiple reasons:
    # CPython does not support parallel CPU bound tasks
    # like model inference on threads due to the CPython's
    # Global Interpreter lock. In the future I am certain I may
    # switch to use a GPU with OpenCL, since that offloads computation
    # to GPU and makes the process I/O bound (PCIe).
    #
    # Python signals become more complicated if we declare non-daemon threads.
    #
    # If it turns of that CPU matrix multiplication is too slow
    # it is best to use Intel's MKL before making any major architectural
    # decisions.
    _formats = None
    _chars = range(97, 122) + range(48, 57) + [95]
    '''
    _operation_handler = {
        'formats': ShowdownClient.formats_action,
        'title': Battle.title_action,
        'updatesearch': updatesearch_action,
        #'updatechallenges': self.updatechallenges_action,
        'queryresponse': queryresponse_action,
        'updateuser': updateuser_action,
        'challstr': challstr_action,
        #'nametaken': self.nametaken_action,
        'request': self.request_action,
        'init': self.init_action,

        #'-fieldstart': self.fieldstart_action,
        #'-fieldend': self.fieldend_action,
        #'-sidestart': self.sidestart_action,
        #'-sideend': self.sideend_action,
        '-boost': self.boost_action,
        '-unboost': self.unboost_action,
        '-item': self.item_action,
        '-enditem': self.enditem_action,
        '-heal': self.heal_action,
        '-weather': Battle.weather_action,
        '-status': Pokemon.status_action,
        '-ability': Pokemon.ability_action,
        '-drag': self.drag_action,
        #'-supereffective': self.supereffective_action,
        #'-resisted': self.resisted_action,
        #'-immune': sel.immune_action,
        '-damage': self.damage_action,
        '-fail': self.fail_action,

        'teamsize': self.teamsize_action,
        #'cant': self.cant_action,
        #'miss': self.miss_action,
        'player': Battle.player_action,
        #'detailschange': self.detailschange_action,
        'join': self.join_action,
        'switch': self.switch_action,
        'turn': self.turn_action,
        'move': self.move_action,
        'faint': self.faint_action,
        'win': self.win_action,

        'j': self.join_action,
        'J': self.join_action,
        'l': self.leave_action,
        'L': self.leave_action,
        'chat': self.chat_action,
        'c': self.chat_action,
        'C': self.chat_action,

        '': self.log_message
    }
    '''

    def __init__(self, n_process=4):
        '''
            These attributes are meant for internal use only

            _base: base url for showdown server
            _url: holds completed URL to login to showdown server
            _ws: websocket connection
            _token: randomly generated login guest token
            _chars: randomly sample this to generate random username
            _ioloop: tornado IOloop instance, it is unclear if I even need this TODO
                     I believe it can be made redundant if I use threads
        '''
        self._base = "wss://sim2.psim.us:443/showdown"
        self._url = None
        self._ws = None
        self._token = None
        self._username = None
        self._loggedin = False
        self._avatar = None

        self._pool = []


        self._out_pipes = []
        self._battle_count = []
        self._battle_cache = dict()
        self._n_process = n_process

        for i in range(n_process):
            recv_p, send_p = Pipe(False)
            p = Process(target=self.message_executer, args=(recv_p,))
            p.daemon = True
            self._pool.append(p)
            self._out_pipes.append(send_p)
            self._battle_count.append(0)

    def start(self):
        # start child workers
        [ proc.start() for proc in self._pool]
        print 'Opened pool'

        # start reading from main process
        self._ioloop = IOLoop.instance()
        self.connect()
        self._ioloop.start()

    def __str__(self):
        pass

    def __repr__(self):
        pass

    def generate_URL(self):
        c = lambda s, i: s + chr(i)
        name = reduce(c, random.sample(ShowdownClient._chars, 8), '')

        self._username = name
        self._token = str(random.randint(0, 1000))
        self._url = '/'.join([self._base, self._token, self._username, 'websocket'])

    # TODO: less time spent blocking between reading, parsing, and process hand off
    @gen.coroutine
    def connect(self):
        self.generate_URL()
        print 'Opening Websocket to ' + self._url
        try:
            self._ws = yield websocket_connect(self._url, ping_interval=3, ping_timeout=30)
        except Exception, e:
            red("Could not connect to Showdown")
            red(e.strerror)
        else:
            green("Websocket connected")
            self.read()

    @gen.coroutine
    def read(self):
        while True:
            msg = yield self._ws.read_message()
            if msg is None:
                green("Websocket connection closed.")
                self._ws.close()
                break
            else:
                self.parse(msg)



    def login(self, username, password):
        pass

    def message_executer(self, conn):
        print 'Message execute process: %d started ' % (os.getpid() if hasattr(os, 'getpid') else 'unknown')
        while True:
            message = conn.recv()
            room = None

            # process the message
            for m in message.split('\n'):
                if m == '':
                    continue
                if m[0] == DELIM:
                    sep = m.find(DELIM, 1)
                    if sep == -1:
                        op = ''
                        data = m[1:]
                    else:
                        op = m[1:sep]
                        data = m[sep+1:]

                    green('Executing op: ' + op + ' data: ' + data)
                    self.execute(room, op, data)
                else:  # should be printed to room log
                    if m[0] == MSG_HEAD:
                        room = m[1:]
                    else:
                        self.log_message('NO ROOM', m)

    def execute(self, room, operation, data):
        if data == '':
            return
        if operation in ShowdownClient._operation_handler:
            #ShowdownClient._operation_handler[operation](room, data)
            pass
        else:
            yellow("Unhandled operation: " + operation)


    def parse(self, message):
        room = None
        message = message.decode('unicode_escape')
        if (message[:3] != 'a["') or (message[-2:] != '"]'):
            red('Bad input format: ' + message)
        else:
            # message format is good, pass to correct child
            message_content = message[3:-2]
            #green(message_content)

            if message_content[0] == '>':
                room_end = message_content.find('\n')
                room = message_content[1:room_end]
            else:
                room = ''

            # find process to assign battle to
            proc_num = self._battle_cache.get(room)
            if not proc_num:
                proc_num = random.randint(0, self._n_process-1)
                self._battle_cache[room] = proc_num
            self._out_pipes[proc_num].send(message_content)








if __name__ == '__main__':
    freeze_support()
    ps = ShowdownClient()
    ps.start()
