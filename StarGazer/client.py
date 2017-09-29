'''
    Pokemon Showdown Client class


1. client side behaviours
    - connecting to showdown server
    - logging in to showdown account
    - requesting matches from other players
    - fetching game state, i.e did other player move, parsing moves,
    - manging opponent timeout, quits
    - sending responses to showdown server
    - accepting match requests from players
    - supports many concurrent matches at once to learn from
    - cannot be single threaded networking code

'''

# logging.warn
# logging.debug,info,warning,error,critical,exception

import pdb
import random

import logging
from logging.config import dictConfig

import tornado

from tornado.websocket import websocket_connect
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen

import re
import requests
import json


# on error torado does not throw exceptions
# how to handle these?

# how to close websocket?

class Client:
    def __init__(self):
        self.base = "wss://sim2.psim.us:443/showdown"
        self.url = None

        self.playername = None
        self.loggedin = False
        self.avatar = None
        self.battles = None
        self.battleState = None

        self.chars = range(97, 122) + range(48, 57) + [95]
        self.username = None
        self.token = None
        self.ws = None

        self.operation_handler = {
            'chat': self.chat_action,
            'formats': self.formats_action,
            'updatesearch': self.updatesearch_action,
            'updatechallenges': self.updatechallenges_action,
            'queryresponse': self.queryresponse_action,
            'updateuser': self.updateuser_action,
            'challstr': self.challstr_action,
            'nametaken': self.nametaken_action,
            '': self.log_message,
        }

        self.ioloop = IOLoop.instance()
        self.connect()
        # PeriodicCallback(self.keep_alive, 20000, io_loop=self.ioloop).start()
        self.ioloop.start()

    @gen.coroutine
    def connect(self):
        self.generate_URL()
        print '<URL IS>: %s' % self.url
        try:
            self.ws = yield websocket_connect(self.url)
        except Exception, e:
            print "Could not connect to Showdown"
            print e.strerror
        else:
            print "Connected!"
            self.run()

    @gen.coroutine
    def run(self):
        while True:
            msg = yield self.ws.read_message()
            if msg is None:
                print "Connection closed."
                self.ws = None
                self.username = None
                break
            else:
                self.parse_message(msg)

    def generate_URL(self):
        c = lambda s, i: s + chr(i)
        name = reduce(c, random.sample(self.chars, 8), '')

        self.username = name
        self.token = str(random.randint(0, 1000))
        self.url = '/'.join([self.base, self.token, self.username, 'websocket'])

    def parse_message(self, message):
        room = None
        message = message.decode('unicode_escape')
        content_match = re.match('a\["(.*)"\]', message, flags=re.DOTALL)
        if not content_match:
            self.log_message('bad_requests', message)
            return
        m_data = content_match.group(1)
        print '<MESSAGE DATA>:\n' + m_data
        message_lines = m_data.split('\n')

        print '<MESSAGE COUNT>: ' + str(len(message_lines))

        for m in message_lines:
            if m == '':
                continue
            if m[0] == '|':
                sep = m.find('|', 1)
                if sep == -1:
                    op = ''
                    data = m[1:]
                else:
                    op = m[1:sep]
                    data = m[sep+1:]

                print 'EXECUTE: <OP>: ' + op + ' <DATA>: ' + data
                self.execute(room, op, data)
            else:  # should be printed to room log
                if m[0] == '>':
                    room = m[1:]
                    print '<ROOM>: ' + room
                else:
                    self.log_message(room, m)
            print('\n')

    def updateuser_action(self, room, data):
        self.playername, loggedin, self.avatar = data.split('|')
        self.loggedin = (loggedin == '1')
        print "<UPDATEUSER>:"
        print "Updating user..."
        print "Your playername: " + self.playername
        print ("You are logged in" if self.loggedin else "You are not logged in")
        print "Your avatar is " + self.avatar

    def log_message(self, room, message):
        print "<LOG MESSAGE>: " + room + ': ' + message

    def execute(self, room, operation, data):
        if data == '':
            return
        if operation in self.operation_handler:
            self.operation_handler[operation](room, data)
        else:
            print "<GOT UNHANDLED OP>: " + operation

    def chat_action(self, room, data):
        if not room:
            room = 'None'
        print '<CHAT>: ' + room + ': ' + data

    def join_action(self, room, data):
        if not room:
            room = 'None'
        print '<JOIN>: ' + room + ': ' + data

    def formats_action(self, room, data):
        print '\n'.join(["<FORMAT>: " + d for d in data.split(',')])

    def updatesearch_action(self, room, data):
        battles = json.loads(data)
        current_games = battles['games']
        print "<UPDATE SEARCH>: Looking for %d battles, playing %d" % (len(battles['searching']), len(current_games) if current_games else 0)
        self.battles = battles

    def updatechallenges_action(self, room, data):
        pass

    def queryresponse_action(self, room, data):
        pass

    def challstr_action(self, room, data):
        # if cookies GET  http://play.pokemonshowdown.com/action.php?act=upkeep&challstr=CHALLSTR
        # else HTTP POST request to http://play.pokemonshowdown.com/action.php with the data act=login&name=USERNAME&pass=PASSWORD&challstr=CHALLSTR
        #  Note that CHALLSTR contains | characters. (Also feel free to make the request to https:// if your client supports it.)
        #Either way, the response will start with ] and be followed by a JSON object which we'll call data.
        # Finish logging in (or renaming) by sending: /trn USERNAME,0,ASSERTION where USERNAME is your desired username and ASSERTION is data.assertion.
        payload = {
            'act': 'login',
            'name': "Sooham Rafiz",
            'challstr': data,
            'pass': 'zHYCxfZg26V5'
        }
        resp = requests.post('https://play.pokemonshowdown.com/action.php', data=payload)
        if (resp.status_code == 200):
            print '<RESPONSE>: ' + resp.text
            print '<WRITING>:' + '"|/trn ' + ','.join(["Sooham Rafiz", '0', json.loads(resp.text[1:])['assertion']]) + '"'
            self.ws.write_message('"|/trn ' + ','.join(["Sooham Rafiz", '0', json.loads(resp.text[1:])['assertion']]) + '"')
        else:
            print '<ERROR>: challstr response not 200'

    def init_battle(self):
        self.ws.write_message("|/search gen7randombattle")




    def nametaken_action(self, room, data):
        pass

if __name__ == "__main__":
    logging_config = dict(
        version = 1,
        formatters = {
            'f': {'format':
                  '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'}
            },
        handlers = {
            'h': {'class': 'logging.StreamHandler',
                  'formatter': 'f',
                  'level': logging.DEBUG}
            },
        loggers = {
            'tornado.general': {'handlers': ['h'],
                     'level': logging.DEBUG}
            }
    )
    dictConfig(logging_config)
    logger = logging.getLogger()

    Client()
