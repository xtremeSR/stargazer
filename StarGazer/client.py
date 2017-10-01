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

import time
import threading

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
        self.battleState = dict()

        self.chars = range(97, 122) + range(48, 57) + [95]
        self.username = None
        self.token = None
        self.ws = None
        self.terminal_lock = threading.Lock()

        self.operation_handler = {
            'formats': self.formats_action,
            'updatesearch': self.updatesearch_action,
            'updatechallenges': self.updatechallenges_action,
            'queryresponse': self.queryresponse_action,
            'updateuser': self.updateuser_action,
            'challstr': self.challstr_action,
            'nametaken': self.nametaken_action,
            'request': self.request_action,
            'init': self.init_action,
            '-fieldstart': self.fieldstart_action,
            '-damage': self.damage_action,
            '-fail': self.fail_action,
            '-sidestart': self.sidestart_action,
            '-heal': self.heal_action,
            '-status': self.status_action,
            'teamsize': self.teamsize_action,
            'title': self.title_action,
            'player': self.player_action,
            'join': self.join_action,
            'switch': self.switch_action,
            'j': self.join_action,
            'J': self.join_action,
            'l': self.leave_action,
            'win': self.win_action,
            'L': self.leave_action,
            'chat': self.chat_action,
            'c': self.chat_action,
            'C': self.chat_action,
            'turn': self.turn_action,
            '': self.log_message
        }

        self.ioloop = IOLoop.instance()
        self.connect()
        # PeriodicCallback(self.keep_alive, 20000, io_loop=self.ioloop).start()
        self.ioloop.start()

    def send_command_to_showdown(self):
        while True:
            raw_input()
            with self.terminal_lock:
                command = raw_input("PS >> ").strip()
                print "<SEND COMMAND>: " + command
                if command == 'start':
                    self.init_battle()
                elif command.startswith('forfeit'):
                    if len(self.battles):
                        print "Which battle would you like to forfeit?"
                        for i in range(len(self.battles)):
                            print str(i) + '. ' + self.battles[i]
                        battle_num = int(raw_input('battle int > ').strip())
                        if 0 <= battle_num < len(self.battles):
                            self.forfeit_battle(self.battles[battle_num])
                    else:
                        print "There are no current active battles"
                elif command.startswith('choose'):
                    print "Choosing move..."
                    print "Which battle would you like to choose for?"
                    for i in range(len(self.battles)):
                        print str(i) + '. ' + self.battles[i]
                    battle_num = int(raw_input('battle int > ').strip())
                    battle = self.battleState[self.battles[battle_num]]
                    print "Which move in battle would you like to choose?"
                    move_selected = []
                    for pokemon in battle[battle['you']]['active']:
                        for j in range(len(pokemon["moves"])):
                            move = pokemon['moves'][j]
                            print str(j + 1) + '. ' + move["move"] + " (" + str(move["pp"]) + "/" + str(move["maxpp"]) + ")" + (" disabled" if move["disabled"] else "")
                        for j in range(len(pokemon["canZMove"])):
                            move = pokemon['moves'][j]
                            print str(j + 5) + '. ' + move["move"] + " (1/1)"
                        move_int = int(raw_input("move > "))
                        if move_int > 4:
                            move_selected.extend([str(move_int - 4), 'zmove'])
                        else:
                            move_selected.append(str(move_int))
                    self.choose(self.battles[battle_num], "move", move_selected)

                elif command == 'custom':
                    self.ws.write_message(raw_input('custom command > '))


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
            input_thread = threading.Thread(target=self.send_command_to_showdown)
            input_thread.daemon = True
            input_thread.start()


    @gen.coroutine
    def run(self):
        while True:
            msg = yield self.ws.read_message()
            if msg is None:
                with self.terminal_lock:
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
            self.log_message('BAD FORMAT', message)
            return
        m_data = content_match.group(1)
        with self.terminal_lock:
            print '<MESSAGE DATA>:\n' + m_data
        message_lines = m_data.split('\n')

        with self.terminal_lock:
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

                with self.terminal_lock:
                    print 'EXECUTE: <OP>: ' + op + ' <DATA>: ' + data
                self.execute(room, op, data)
            else:  # should be printed to room log
                if m[0] == '>':
                    room = m[1:]
                    with self.terminal_lock:
                        print '<ROOM>: ' + room
                else:
                    self.log_message('NO ROOM', m)

    def updateuser_action(self, room, data):
        self.playername, loggedin, self.avatar = data.split('|')
        self.loggedin = (loggedin == '1')
        with self.terminal_lock:
            print "<UPDATEUSER>:"
            print "Updating user..."
            print "Your playername: " + self.playername
            print ("You are logged in" if self.loggedin else "You are not logged in")
            print "Your avatar is " + self.avatar

    def log_message(self, room, message):
        with self.terminal_lock:
            if message == 'start':
                print '<STARTED>'
                print 'LET AI TAKE CONTROL FROM HERE ON'
            else:
                print "<LOG MESSAGE>: " + room + ': ' + message

    def switch_action(self, room, data):
        # this is only place where you can gain information about the opponent's pokemon
        pokemon, details, condition = data.split('|')
        player_token, pokemon_name = pokemon.split(':')
        player_token = player_token[:2]
        pokemon_name = pokemon_name.strip()

        if player_token == self.battleState[room]['you']:
            switch_success = False
            for pokemon in self.battleState[room][player_token]["pokemon"]:
                if pokemon['details'] == details and pokemon['condition'] == condition:
                    pokemon['active'] = True
                    switch_success = True
                else:
                    pokemon['active'] = False

            if not switch_success:
                print 'Could not find switched in pokemon: ' + details
                pdb.set_trace()
        else:
            # this is the opponent, we can store info on his pokemon
            if "pokemon" not in self.battleState[room][player_token]:
                self.battleState[room][player_token]["pokemon"] = []

            is_new_pokemon = True
            for pokemon in self.battleState[room][player_token]["pokemon"]:
                if pokemon['details'] == details:
                    pokemon['active'] = True
                    pokemon['condition'] = condition
                    is_new_pokemon = False
                else:
                    pokemon['active'] = False

            if is_new_pokemon:
                self.battleState[room][player_token]["pokemon"].append(
                    {
                        'ident': player_token + ': ' + pokemon_name,
                        'ability': None,
                        'items': None,
                        'details': details,
                        'active': True,
                        'moves': [],
                        'condition': condition
                    }
                )


    def fieldstart_action(self, room, data):
        field_info = data.split('|')
        field_name = field_info[0]
        with self.terminal_lock:
            print '<FIELDSTART> ' + field_name
        self.battleState[room]['field'] = field_name

    def fieldend_action(self, room, data):
        pass

    def heal_action(self, room, data):
        #p1a: Bronzong|93/100 brn|[from] item: Leftovers
        #p2a: Moltres|252/271|[from] item: Leftovers
        heal_info = data.split('|')
        player_token = heal_info[0][:2]
        healed_pokemon = heal_info[0][5:]
        condition = heal_info[1]

        for pokemon in self.battleState[room][player_token]["pokemon"]:
            if pokemon['ident'] == player_token + ': ' + healed_pokemon:
                pokemon['condition'] = condition
                break

    def status_action(self, room, data):
        #p1a: Bronzong|brn|[from] ability: Flame Body|[of] p2a: Moltres
        heal_info = data.split('|')
        player_token = heal_info[0][:2]
        healed_pokemon = heal_info[0][5:]
        condition = heal_info[1]

        for pokemon in self.battleState[room][player_token]["pokemon"]:
            if pokemon['ident'] == player_token + ': ' + healed_pokemon:
                if len(pokemon['condition'].split(' ')) == 1:
                    pokemon['condition'] += ' ' + condition
                break

    def execute(self, room, operation, data):
        if data == '':
            return
        if operation in self.operation_handler:
            self.operation_handler[operation](room, data)
        else:
            with self.terminal_lock:
                print "<GOT UNHANDLED OP>: " + operation

    def chat_action(self, room, data):
        if not room:
            room = 'None'
        with self.terminal_lock:
            print '<CHAT>: ' + room + ': ' + data

    def weather_action(self, room, data):
        weather_data = data.split('|')

    def join_action(self, room, data):
        if not room:
            room = 'None'
        with self.terminal_lock:
            print '<JOIN>: ' + room + ': ' + data

    def leave_action(self, room, data):
        if data == self.battleState[room][self.battleState[room]['opponent']]['name']:
            with self.terminal_lock:
                print "OPPONENT LEFT!"
            self.forfeit_battle(room)

    def win_action(self, room, data):
        if room in self.battles:
            with self.terminal_lock:
                if data == 'Sooham Rafiz':
                    print "YOU WON!"
                else:
                    print "YOU LOST :("

    def turn_action(self, room, data):
        #3
        self.battleState[room]['turn'] = int(data)
        with self.terminal_lock:
            print '<TURN NUMBER> ' + data

    def init_action(self, room, data):
        if data == 'battle':
            self.battleState[room] = dict()
            self.battleState[room]['p1'] = dict()
            self.battleState[room]['p2'] = dict()

    def player_action(self, room, data):
        player_token, player_name, _ = data.split('|')
        self.battleState[room][player_token]['name'] = player_name
        if player_name == 'Sooham Rafiz':
            self.battleState[room]['you'] = player_token
        else:
            self.battleState[room]['opponent'] = player_token

    def teamsize_action(self, room, data):
        player_token, teamsize = data.split('|')
        self.battleState[room][player_token]['teamsize'] = int(teamsize)

    def request_action(self, room, data):
        # {"active":[{"moves":[{"move":"Thunderbolt","id":"thunderbolt","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Focus Blast","id":"focusblast","pp":8,"maxpp":8,"target":"normal","disabled":false},{"move":"Nasty Plot","id":"nastyplot","pp":32,"maxpp":32,"target":"self","disabled":false},{"move":"Surf","id":"surf","pp":24,"maxpp":24,"target":"allAdjacent","disabled":false}],"canZMove":[{"move":"Stoked Sparksurfer","target":"normal"},null,null,null]}],"side":{"name":"Sooham Rafiz","id":"p1","pokemon":[{"ident":"p1: Raichu","details":"Raichu-Alola, L83, M","condition":"235/235","active":true,"stats":{"atk":146,"def":131,"spa":205,"spd":189,"spe":230},"moves":["thunderbolt","focusblast","nastyplot","surf"],"baseAbility":"surgesurfer","item":"aloraichiumz","pokeball":"pokeball","ability":"surgesurfer"},{"ident":"p1: Xurkitree","details":"Xurkitree, L76","condition":"251/251","active":false,"stats":{"atk":140,"def":152,"spa":307,"spd":152,"spe":170},"moves":["energyball","dazzlinggleam","voltswitch","thunderbolt"],"baseAbility":"beastboost","item":"choicescarf","pokeball":"pokeball","ability":"beastboost"},{"ident":"p1: Terrakion","details":"Terrakion, L77","condition":"267/267","active":false,"stats":{"atk":243,"def":183,"spa":155,"spd":183,"spe":211},"moves":["swordsdance","earthquake","closecombat","stoneedge"],"baseAbility":"justified","item":"lifeorb","pokeball":"pokeball","ability":"justified"},{"ident":"p1: Kartana","details":"Kartana, L75","condition":"212/212","active":false,"stats":{"atk":315,"def":240,"spa":132,"spd":90,"spe":207},"moves":["leafblade","sacredsword","swordsdance","psychocut"],"baseAbility":"beastboost","item":"lifeorb","pokeball":"pokeball","ability":"beastboost"},{"ident":"p1: Braviary","details":"Braviary, L81, M","condition":"295/295","active":false,"stats":{"atk":246,"def":168,"spa":139,"spd":168,"spe":176},"moves":["return","bulkup","superpower","substitute"],"baseAbility":"defiant","item":"leftovers","pokeball":"pokeball","ability":"defiant"},{"ident":"p1: Comfey","details":"Comfey, L79, M","condition":"210/210","active":false,"stats":{"atk":128,"def":188,"spa":175,"spd":219,"spe":204},"moves":["toxic","aromatherapy","uturn","synthesis"],"baseAbility":"naturalcure","item":"leftovers","pokeball":"pokeball","ability":"naturalcure"}]},"rqid":2}
        pokemon_data = json.loads(data)

        player_token = pokemon_data["side"]["id"]

        self.battleState[room][player_token]["pokemon"] = pokemon_data["side"]["pokemon"]
        self.battleState[room][player_token]["rqid"] = str(pokemon_data["rqid"])
        if 'active' in pokemon_data:
            self.battleState[room][player_token]["active"] = pokemon_data["active"]

    def damage_action(self, room, data):
        #p2a: Vespiquen|0 fnt
        #p1a: Bronzong|87/100 brn|[from] brn
        damage_info = data.split('|')
        player_token = damage_info[0][:2]
        damaged_pokemon = damage_info[0][5:]
        condition = damage_info[1]

        for pokemon in self.battleState[room][player_token]["pokemon"]:
            if pokemon['ident'] == player_token + ': ' + damaged_pokemon:
                pokemon['condition'] = condition
                break


    def title_action(self, room, data):
        if self.battleState[room]:
            self.battleState[room]['title'] = data

    def formats_action(self, room, data):
        with self.terminal_lock:
            print '\n'.join(["<FORMAT>: " + d for d in data.split(',')])

    def choose(self, room, action, items):
        # battle-gen7randombattle-639184562|/choose move 1 zmove|2
        resp = '"' + room + "|/choose " + action + " " + items.join(' ') + "|" + self.battleState[room][self.battleState[room]['you']]['rqid'] + '"'
        print "<MOVE>"
        print "<RESPONSE> " + resp
        self.ws.write_message(resp)

    def updatesearch_action(self, room, data):
        battles = json.loads(data)
        current_games = battles['games']
        with self.terminal_lock:
            print "<UPDATESEARCH>: Looking for %d battles, playing %d" % (len(battles['searching']), len(current_games) if current_games else 0)
        self.battles = current_games.keys() if current_games else []

    def fail_action(self, room, data):
        # send AI a bad signal here
        pass

    def immune_action(self, room, data):
        # send AI a bad signal here
        pass

    def sidestart_action(self, room, data):
        #p1: u05431ujijklk|Spikes
        side_info = data.split('|')
        side_name = side_info[1]
        with self.terminal_lock:
            print '<SIDESTART> ' + side_name
        self.battleState[room]['side'] = side_name

    def sideend_action(self, room, data):
        pass

    def updatechallenges_action(self, room, data):
        pass

    def queryresponse_action(self, room, data):
        query_type, json_data = data.split('|')
        json_data = json.loads(json_data)
        if not json_data:
            json_data = '(Empty)'
        with self.terminal_lock:
            print '<QUERY RESP>: querytype: ' + query_type + ' query JSON: ' + json_data

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
            with self.terminal_lock:
                print '<RESPONSE>: ' + resp.text
                print '<WRITING>:' + '"|/trn ' + ','.join(["Sooham Rafiz", '0', json.loads(resp.text[1:])['assertion']]) + '"'
            self.ws.write_message('"|/trn ' + ','.join(["Sooham Rafiz", '0', json.loads(resp.text[1:])['assertion']]) + '"')
        else:
            with self.terminal_lock:
                print '<ERROR>: challstr response not 200'

    def init_battle(self):
        self.ws.write_message('"|/search gen7randombattle"')

    def forfeit_battle(self, battle_room):
        self.ws.write_message('"' + battle_room + '|/forfeit"')
        self.ws.write_message('"|/leave ' + battle_room + '"')


    def nametaken_action(self, room, data):
        pass


if __name__ == "__main__":
    logging_config = dict(
        version=1,
        formatters={
            'f': {'format':
                  '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'}
            },
        handlers={
            'h': {'class': 'logging.StreamHandler',
                  'formatter': 'f',
                  'level': logging.DEBUG}
            },
        loggers={
            'tornado.general': {
                'handlers': ['h'],
                'level': logging.DEBUG
            }
        }
    )

    dictConfig(logging_config)
    logger = logging.getLogger()

    Client()
