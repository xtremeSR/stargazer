#! python

import pdb

import requests
import random
import re
import json
import time
from multiprocessing import Pipe, Process, freeze_support
# import psutil
import argparse
import sys
import os

from collections import defaultdict

import tornado
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.websocket import websocket_connect

from .utils import *
from .Battle import Battle
from .Player import Player
from .Pokemon import Pokemon

from .HumanAgent import HumanAgent
'''
    File: ShowdownClient.py
    Description: ShowdownClient represents the Websocket client for connecting
    to, parsing messages from, sending responses to the server.
'''

# TODO: special case for ditto

DELIM = '|'
MSG_HEAD = '>'
LOGIN_URL = 'https://play.pokemonshowdown.com/action.php'
ROOT_URL = "http://play.pokemonshowdown.com/"


class ShowdownClient:
    # This class uses multiprocessing and IPC
    # to map on server messages to a process pool.
    #
    # This architecture was chosen for multiple reasons:
    # CPython does not support parallel CPU bound tasks
    # like model inference on threads due to the CPython's
    # Global Interpreter lock. In the future I am certain I shall
    # switch to use a GPU with OpenCL, since that offloads computation
    # to GPU and makes the process I/O bound (PCIe).
    #
    # Python signals become more complicated if we declare non-daemon threads.
    #
    # If it turns out that CPU matrix multiplication is too slow
    # it is best to use Intel's MKL before making any major architectural
    # decisions.
    _formats = None
    _chars = range(97, 122) + range(48, 57) + [95]

    def __init__(self, username, password, n_process=4, agent_cls=HumanAgent):
        '''
            These attributes are meant for internal use only.

            username: client account username
            password: client account password

            _base: base url for showdown server
            _url: holds completed URL to login to showdown server
            _ws: websocket connection
            _token: randomly generated login guest token
            __: random username used to initially login
            _loggedin: is player logged in?
            _avatar: the player avatar
            _ioloop: Tornado IOLoop.
            _pool: list of subprocesses.
            _out_pipes: pipes connecting to processes
            _battle_count: number of battles handled per subprocess
            _battle_to_process:
            _n_process: number of processes for pool.
        '''
        self.username = username
        self.password = password

        self._base = "ws://sim2.psim.us:80/showdown"
        self._url = None
        self._ws = None
        self._token = None
        self.__ = None
        self._loggedin = False
        self._avatar = None
        self._ioloop = None

        self._pool = []

        self._out_pipes = []
        self._battle_count = []
        self._battle_to_process = dict()
        self.battles = defaultdict(Battle)
        self._n_process = n_process

        self._agent_cls = agent_cls
        self._agent = None

        self._operation_handler = {
            '':                 self.log_message,
            '-ability':         self.ability_action,
            '-activate':        self.activate_action,
            '-boost':           self.boost_action,
            '-crit':            self.crit_action,
            '-damage':          self.damage_action,
            '-drag':            self.drag_action,
            '-end':             self.end_action,
            '-enditem':         self.enditem_action,
            '-fail':            self.fail_action,
            '-fieldend':        self.fieldend_action,
            '-fieldstart':      self.fieldstart_action,
            '-heal':            self.heal_action,
            '-immune':          self.immune_action,
            '-item':            self.item_action,
            '-resisted':        self.resisted_action,
            '-sideend':         self.sideend_action,
            '-sidestart':       self.sidestart_action,
            '-start':           self.start_action,
            '-status':          self.status_action,
            '-supereffective':  self.supereffective_action,
            '-unboost':         self.unboost_action,
            '-weather':         self.weather_action,
            'L':                self.leave_action,
            'cant':             self.cant_action,
            'challstr':         self.challstr_action,
            'detailschange':    self.detailschange_action,
            'faint':            self.faint_action,
            'formats':          self.formats_action,
            'gametype':         self.gametype_action,
            'gen':              self.gen_action,
            'init':             self.init_action,
            #'join':             self.join_action,
            'l':                self.leave_action,
            'miss':             self.miss_action,
            'move':             self.move_action,
            #'nametaken':        self.nametaken_action,
            'player':           self.player_action,
            'queryresponse':    self.queryresponse_action,
            'request':          self.request_action,
            'start':            self.start_action,
            'switch':           self.switch_action,
            'teamsize':         self.teamsize_action,
            'title':            self.title_action,
            'turn':             self.turn_action,
            #'updatechallenges': self.updatechallenges_action,
            'updatesearch':     self.updatesearch_action,
            'updateuser':       self.updateuser_action,
            'win':              self.win_action,
        }

        for i in range(n_process):
            recv_p, send_p = Pipe(False)
            p = Process(target=ShowdownClient.message_executer, args=(self, recv_p))
            p.daemon = True
            self._pool.append(p)
            self._out_pipes.append(send_p)
            self._battle_count.append(0)


    def start(self):
        # start reading from main process
        self._ioloop = IOLoop.instance()
        self.connect()
        self._ioloop.start()

#    def __str__(self):
#        pass

#    def __repr__(self):
#        pass

    def generate_URL(self):
        c = lambda s, i: s + chr(i)
        name = reduce(c, random.sample(ShowdownClient._chars, 8), '')

        self.__ = name
        self._token = str(random.randint(0, 1000))
        self._url = '/'.join([self._base, self._token, self.__, 'websocket'])

    # TODO: less time spent blocking between reading, parsing, and process hand off
    @gen.coroutine
    def connect(self):
        self.generate_URL()
        print 'Opening Websocket to ' + self._url
        try:
            self._ws = yield websocket_connect(self._url, ping_interval=3, ping_timeout=30)
            # start child workers
            self._agent = self._agent_cls(self._ws, self)
            [proc.start() for proc in self._pool]
            print 'Opened pool'
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

    def parse(self, message):
        room = None
        message = message.decode('unicode_escape')
        if (message[:3] != 'a["') or (message[-2:] != '"]'):
            red('Bad message received format: ' + message)
        else:
            # message format is good, pass to correct child
            message_content = message[3:-2]
            #green(message_content)

            if message_content[0] == MSG_HEAD:
                room_end = message_content.find('\n')
                room = message_content[1:room_end]
            else:
                room = ''

            # find process to assign battle to
            proc_num = self._battle_to_process.get(room)
            if not proc_num:
                proc_num = random.randint(0, self._n_process-1)
                self._battle_to_process[room] = proc_num
            self._out_pipes[proc_num].send(room + DELIM + message_content)


    def log_message(self, room, message):
        yellow("LOG: " + room + ': ' + message)

    def start_battle(self):
        self._ws.write_message('"|/search gen7randombattle"')


    def forfeit_battle(self, battle_room):
        self._ws.write_message('"' + battle_room + '|/forfeit"')
        self._ws.write_message('"|/leave ' + battle_room + '"')

    # ------------ ACTIONS --------------

    def crit_action(self, room, data):
        # |-crit|p1a: Sharpedo
        # if you bad
        pass

    def formats_action(self, room, data):
        green('\n'.join([d for d in data.split(',')]))

    def gen_action(self, room, generation):
        # |gen|7
        self.battles[room].generation = int(generation)

    def gametype_action(self, room, gametype):
        # |gametype|singles
        self.battles[room].gametype = gametype

    def title_action(self, room, title):
        # |title|Anime sand vs. Sooham Rafiz
        if not self.battles.has_key(room):
            self.battles[room]
        self.battles[room].title = title

    def updatesearch_action(self, room, data):
        # |updatesearch|{"searching":[],"games":{"battle-gen7ubers-640967362":"[Gen 7] Ubers Battle*"}}
        # |updatesearch|{"searching":["gen7ubers"],"games":null}
        battles = json.loads(data)
        current_games = battles['games']
        print "Looking for %d battles, playing %d" % (len(battles['searching']), len(current_games) if current_games else 0)
        # TODO: should I add a new battle seen in data to a subprocess
        # and _battle_to_process?
        #for battle in current_games:
        #    proc_num = self._battle_to_process.get(battle)
        #    if not proc_num:

    def updateuser_action(self, room, data):
        playername, loggedin, avatar = data.split('|')
        if playername == self.username and not self._loggedin:
            self._loggedin = loggedin
            self._avatar = avatar
            print "Updating User"
            print "Player: " + playername
            print ("Logged in" if loggedin else "Not logged in")

            self._agent.start_battle()
        else:
            yellow("Multiple login attempts.")

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
            # with self.terminal_lock:
            self._ws.write_message('"|/trn ' + ','.join(["Sooham Rafiz", '0', json.loads(resp.text[1:])['assertion']]) + '"')
        else:
            red('Error: challstr response not 200')
        payload = {
            'act': 'login',
            'name': self.username,
            'challstr': data,
            'pass': self.password
        }
        print "Logging in..."
        resp = requests.post(LOGIN_URL, data=payload)
        if (resp.status_code == 200):
            self._ws.write_message('"|/trn ' + ','.join([self.username, '0', json.loads(resp.text[1:])['assertion']]) + '"')
        else:
            red('challstr response not 200')

    def request_action(self, room, data):
        # {"active":[{"moves":[{"move":"Thunderbolt","id":"thunderbolt","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Focus Blast","id":"focusblast","pp":8,"maxpp":8,"target":"normal","disabled":false},{"move":"Nasty Plot","id":"nastyplot","pp":32,"maxpp":32,"target":"self","disabled":false},{"move":"Surf","id":"surf","pp":24,"maxpp":24,"target":"allAdjacent","disabled":false}],"canZMove":[{"move":"Stoked Sparksurfer","target":"normal"},null,null,null]}],"side":{"name":"Sooham Rafiz","id":"p1","pokemon":[{"ident":"p1: Raichu","details":"Raichu-Alola, L83, M","condition":"235/235","active":true,"stats":{"atk":146,"def":131,"spa":205,"spd":189,"spe":230},"moves":["thunderbolt","focusblast","nastyplot","surf"],"baseAbility":"surgesurfer","item":"aloraichiumz","pokeball":"pokeball","ability":"surgesurfer"},{"ident":"p1: Xurkitree","details":"Xurkitree, L76","condition":"251/251","active":false,"stats":{"atk":140,"def":152,"spa":307,"spd":152,"spe":170},"moves":["energyball","dazzlinggleam","voltswitch","thunderbolt"],"baseAbility":"beastboost","item":"choicescarf","pokeball":"pokeball","ability":"beastboost"},{"ident":"p1: Terrakion","details":"Terrakion, L77","condition":"267/267","active":false,"stats":{"atk":243,"def":183,"spa":155,"spd":183,"spe":211},"moves":["swordsdance","earthquake","closecombat","stoneedge"],"baseAbility":"justified","item":"lifeorb","pokeball":"pokeball","ability":"justified"},{"ident":"p1: Kartana","details":"Kartana, L75","condition":"212/212","active":false,"stats":{"atk":315,"def":240,"spa":132,"spd":90,"spe":207},"moves":["leafblade","sacredsword","swordsdance","psychocut"],"baseAbility":"beastboost","item":"lifeorb","pokeball":"pokeball","ability":"beastboost"},{"ident":"p1: Braviary","details":"Braviary, L81, M","condition":"295/295","active":false,"stats":{"atk":246,"def":168,"spa":139,"spd":168,"spe":176},"moves":["return","bulkup","superpower","substitute"],"baseAbility":"defiant","item":"leftovers","pokeball":"pokeball","ability":"defiant"},{"ident":"p1: Comfey","details":"Comfey, L79, M","condition":"210/210","active":false,"stats":{"atk":128,"def":188,"spa":175,"spd":219,"spe":204},"moves":["toxic","aromatherapy","uturn","synthesis"],"baseAbility":"naturalcure","item":"leftovers","pokeball":"pokeball","ability":"naturalcure"}]},"rqid":2}
        pokemon_data = json.loads(data)
        idx = pokemon_data["side"]["id"]
        player = self.battles[room].get_player(idx)
        player.update(pokemon_data)

    def init_action(self, room, data):
        # |init|battle
        # do not delete the line below, look up defaultdict
        self.battles[room]
        self.battles[room].resource_uri = ROOT_URL + room


    def start_action(self, room, data):
        # |-start|p2a: Emolga|Substitute
        # |-start|p2a: Tapu Fini|Substitute
        # |-start| p2a: Golduck|move: Leech Seed
        idx, effect = data.split('|')[:2]
        idx = idx[:2]
        if effect.startswith('move: '):
            effect = effect[6:]
        battle = self.battles[room]
        battle.side_effect[idx][effect] = True

    def end_action(self, room, data):
        # |-end|p1a: Regigigas|Slow Start|[silent]
        idx, effect = data.split('|')[:2]
        idx = idx[:2]
        if effect.startswith('move: '):
            effect = effect[6:]
        battle = self.battles[room]
        if effect in battle.side_effect[idx]:
            del battle.side_effect[idx][effect]

    def fieldstart_action(self, room, data):
        # |-fieldstart|move: Misty Terrain|[from] ability: Misty Surge|[of] p2a: Tapu Fini

        # TODO: get ability of opponent from this
        sdata = data.split('|')
        move = sdata[0]
        battle = self.battles[room]
        if move.startswith('move:'):
            move = move[6:]

        # TODO: regexp
        if len(sdata) > 2 and 'ability:' in sdata[1]:
            ability = sdata[1].split(': ')[1]
            idx = 'p2' if 'p2' in sdata[2] else 'p1'
            pokemon_name = sdata[2].split(': ')[1]
            pkmn = battle.get_player(idx).get_pokemon('ident', pokemon_name)
            if pkmn:
                pkmn.ability = ability
                pkmn.base_ability = ability

        green('Field effect: ' + move)
        battle.field_effect = move

    def fieldend_action(self, room, data):
        # |-fieldend|Misty Terrain
        self.battles[room].field_effect = None

    def sidestart_action(self, room, data):
        #|-sidestart|p1: u05431ujijklk|Spikes
        #-sidestart|p1: Sooham Rafiz|move: Stealth Rock
        #|-sidestart|p2: Zsguita|move: Stealth Rock
        sdata = data.split('|')
        move = sdata[1]
        idx = sdata[0][:2]
        battle = self.battles[room]
        if move.startswith('move:'):
            move = move[6:]

        player = battle.get_player(idx)
        print 'Side effect on player ' + player.name + "'s side: " + move
        battle.side_effect[idx][move] = True

    # TODO: implement side-end
    def sideend_action(self, room, data):
        pass

    def boost_action(self, room, data):
        # |-boost|p1a: Tornadus|atk|1
        # |-boost|p1a: Houndoom|spa|2
        # |-boost|p2a: Serperior|spa|2
        # |-boost|p1a: Samurott|atk|2

        pokemon_data, attr, val = data.split('|')
        idx, pokemon_name = pokemon_data.split(': ')
        idx = idx[:2]
        player = self.battles[room].get_player(idx)
        pkmn = player.get_pokemon('ident', pokemon_name)
        pkmn.boost(attr, int(val))

    def unboost_action(self, room, data):
        # |-unboost|p2a: Manectric|atk|1
        # |-unboost|p2a: Simisage|atk|1
        # |-unboost|p1a: Lumineon|atk|1
        pokemon_data, attr, val = data.split('|')
        idx, pokemon_name = pokemon_data.split(': ')
        idx = idx[:2]
        player = self.battles[room].get_player(idx)
        pkmn = player.get_pokemon('ident', pokemon_name)
        pkmn.unboost(attr, int(val))

    def item_action(self, room, data):
        # |-item|p2a: Carracosta|Air Balloon
        pokemon_data, item = data.split('|')
        idx, pokemon_name = pokemon_data.split(': ')
        idx = idx[:2]

        pkmn = self.battles[room].opponent.get_pokemon('ident', pokemon_name)
        if pkmn:
            pkmn.item = item

    def enditem_action(self, room, data):
        # |-enditem|p2a: Carracosta|Air Balloon
        # |-enditem|p1a: Dragonite|Lum Berry|[eat]
        # |-enditem|p1a: Furfrou|Chesto Berry|[from] move: Knock Off|[of] p2a: Simisage
        sdata = data.split('|')
        idx, pokemon_name = sdata[0].split(': ')
        idx = idx[:2]
        item = sdata[1]

        pkmn = self.battles[room].opponent.get_pokemon('ident', pokemon_name)
        if pkmn:
            pkmn.item = None

    def heal_action(self, room, data):
        #p1a: Bronzong|93/100 brn|[from] item: Leftovers
        #p2a: Moltres|252/271|[from] item: Leftovers
        #p2a: Articuno|69/100|[from] item: Leftovers
        # we can glean information of opponent's item
        data = data.split('|')
        idx = data[0][:2]
        condition = data[1]
        pokemon_name = data[0][5:]

        pkmn = self.battles[room].opponent.get_pokemon('ident', pokemon_name)
        if pkmn and len(data) == 3:
            item = data[2].split(': ')[1]
            green('Opponents ' + pokemon_name + ' holds a ' + item)
            pkmn.item = item
            pkmn.hp, pkmn.status = string_to_condition(condition)

    def weather_action(self, room, data):
        # |-weather|SunnyDay|[upkeep]
        # |-weather|SunnyDay|[upkeep]
        # |-weather|none
        # |-weather| data: Sandstorm|[from] ability: Sand Stream|[of] p2a: Tyranitar
        # |-weather|RainDance|[from] ability: Drizzle|[of] p2a: Kyogre
        # SunnyDay|[from] ability: Drought|[of] p2a: Groudon
        # TODO: scrape ability of pokemon
        if data == 'none':
            self.battles[room].weather = None
        else:
            sdata = data.split('|')
            self.battles[room].weather = sdata[0] if ': ' not in sdata[0] else sdata.split(': ')[1]
            self.battles[room].opponent
            if len(sdata) == 3:
                idx, pokemon_name = sdata[2].split(': ')
                idx = idx[-3:-1]
                if self.battles[room].opponent is self.battles[room].get_player(idx):
                    pkmn = self.battles[room].opponent.get_pokemon('ident', pokemon_name)
                    if pkmn and 'ability' in sdata[1]:
                        pkmn.ability = sdata[1].split(': ')[1]


    def status_action(self, room, data):
        # |-status|p1a: Lunatone|brn
        # |-status|p1a: Bronzong|brn|[from] ability: Flame Body|[of] p2a: Moltres
        # |-status|p2a: Bouffalant|tox
        # |-status|p1a: Beheeyem|tox

        # we can glean ability of opponent's pokemon
        sdata = data.split('|')
        idx = sdata[0][:2]
        status = sdata[1]
        pokemon_name = sdata[0][5:]
        battle = self.battles[room]

        if battle.get_player(idx) is battle.opponent:
            pkmn = battle.opponent.get_pokemon('ident', pokemon_name)
            if pkmn:
                pkmn.status = status
        else:
            content = re.match("ability:\s+?(.+?)\|\[of\] (p1|p2)a: (.+)", data)
            if content:
                ability = content.group(1)
                idd = content.group(2)
                pokemon_name = content.group(3)
                if battle.opponent is battle.get_player(idd):
                    green("Opponents %s's ability is %s" % (pokemon_name, ability))
                    pkmn = battle.opponent.get_pokmon('ident', pokemon_name)
                    if pkmn and ability:
                        pkmn.ability = ability
                        pkmn.base_ability = ability



    def ability_action(self, room, data):
        # |-ability|p1a: Landorus|Intimidate|boost
        data = data.split('|')
        idx, pokemon_name = data[0].split(': ')
        idx = idx[:2]
        ability = data[1]

        if self.battles[room].opponent is self.battles[room].get_player(idx):
            green('Found opponent\'s ' + pokemon_name + ' ability is ' + ability)
            pkmn = self.battles[room].opponent.get_pokemon('ident', pokemon_name)
            if pkmn:
                pkmn.ability = ability
                pkmn.base_ability = ability

    def drag_action(self, room, data):
        # |drag|p1a: Comfey|Comfey, L79, M|210/210
        self.switch(room, data)

    def supereffective_action(self, room, data):
        #|-supereffective|p1a: Muk
        # if player is opponent
        # AI_SEND_REWARD(GOOD)
        # else
        # AI_SEND_REWARD(BAD)
        pass


    def resisted_action(self, room, data):
        # |-resisted|p1a: Lanturn
        # |-resisted|p1a: Lunatone
        # if player is you
        # AI_SEND_REWARD(GOOD)
        # else
        # AI_SEND_REWARD(BAD)
        pass


    def immune_action(self, room, data):
        #|-immune|p1a: Muk|[msg]
        #|-immune|p2a: Solgaleo|[msg]
        #-immune |p1a: Skuntank|[msg]
        sdata = data.split('|')
        idx, pokemon_name = sdata[0].split(': ')
        idx = idx[:2]

        battle = self.battles[room]
        if battle.get_player(idx) is battle.opponent:
            # AI_SEND_REWARD(GOOD)
            red("Opponent's pokemon was immune: " + pokemon_name)
            # tell AI to switch to another pokemon here
        else:
            # AI_SEND_REWARD(BAD)
            green("Your pokemon was immune: " + pokemon_name)


    def damage_action(self, room, data):
        # p2a: Vespiquen|0 fnt
        # p1a: Bronzong|87/100 brn|[from] brn
        # |-damage|p1a: Lanturn|225/343
        # |-damage|p2a: Emboar|88/100|[from] Recoil|[of] p1a: Lanturn
        # |-damage|p2a: Raticate|26/100|[from] item: Life Orb
        # |-damage|p2a: Yanmega|74/100 psn|[from] psn

        damage_info = data.split('|')
        idx = damage_info[0][:2]
        pokemon_name = damage_info[0][5:]
        hp, status = string_to_condition(damage_info[1])
        item = None

        battle = self.battles[room]
        if battle.get_player(idx) is battle.opponent:
            print "is opponent's pokemon"
            pkmn = battle.opponent.get_pokemon('ident', pokemon_name)
            if pkmn:
                print "pokemon valid"
                if len(data) == 3 and 'item' in damage_info[2]:
                    green("pokemon " + pkmn.name + "has item " + item)
                    item = damage_info[2].split(': ')[1]
                    pkmn.item = item
                pkmn.hp = hp
                pkmn.status = status

    def fail_action(self, room, data):
        #|-fail|p2a: Raticate
        # -fail| p2a: Solgaleo|unboost|[from] ability: Full Metal Body|[of] p2a: Solgaleo
        sdata = data.split('|')
        player_token = sdata[0][:2]
        if player_token == self.battleState[room]['you']:
            # AI_SEND_REWARD(BAD)
            red("Your pokemon failed to move: " + pokemon)
            # tell AI to switch to another pokemon here
        else:
            # AI_SEND_REWARD(GOOD)
            green("Opponent's pokemon failed to move: " + pokemon)

    def teamsize_action(self, room, data):
        # |teamsize|p1|6
        idx, team_size = data.split('|')
        battle = self.battles[room]
        battle.get_player(idx).team_size = int(team_size)

    def cant_action(self, room, data):
        #| cant |p2a: Klefki|par
        pass

    def miss_action(self, room, data):
        # |-miss|p2a: Klefki|p1a: Qwilfish
        # |-miss|p2a: Talonflame|p1a: Lunatone
        pass

    def player_action(self, room, data):
        # |player|p1|Sooham Rafiz|102
        # |player|p1|Anime sand|211
        idx, name, _ = data.split('|')
        # the return value below is a defaultdict with Battle factory
        battle = self.battles[room]
        battle.set_player(idx, name)
        if name == self.username:
            battle.you = battle.get_player(idx)
        else:
            battle.opponent = battle.get_player(idx)
            my_idx = "p2" if idx == "p1" else "p1"
            battle.set_player(my_idx, self.username)
            battle.you = battle.get_player(my_idx)


    def activate_action(self, room, data):
        # |-activate|p1a: Registeel|move: Protect
        # |-activate|p2a: Comfey|move: Aromatherapy
        # |-activate|p2a: Tapu Fini|move: Misty Terrain

        pass

    def detailschange_action(self, room, data):
        # |detailschange|p1a: Swampert|Swampert-Mega, L75, F
        # |detailschange|p1a: Gardevoir|Gardevoir-Mega, L77, F
        # |detailschange|p2a: Lucario|Lucario-Mega, L73, F
        sdata = data.split('|')
        idx, pokemon_name = sdata[0].split(': ')
        idx = idx[:2]
        new_pokemon_details = sdata[1].split(', ')
        battle = self.battles[room]
        pkmn = battle.get_player(idx).get_pokemon('ident', pokemon_name)
        if pkmn:
            pkmn.ident = new_pokemon_details[0]
            pkmn.level = int(new_pokemon_details[1][1:]) if len(new_pokemon_details) > 1 else 100
            pkmn.gender = new_pokemon_details[2] if len(new_pokemon_details) > 2 else None



    def switch_action(self, room, data):
        # |switch|p2a: Porygon2|Porygon2, L79|100/100
        # this and drag is only place where you can gain information about the opponent's pokemon
        pokemon, details, condition = data.split('|')
        idx, pokemon_name = pokemon.split(': ')
        idx = idx[:2]
        details = details.split(', ')
        lvl = int(details[1][1:])
        gender = details[2] if len(details) >= 3 else None
        hp, status = string_to_condition(condition)

        battle = self.battles[room]
        if battle.get_player(idx) == battle.you:
            switch_success = False
            for pkmn in battle.you.pokemon:
                if pkmn.ident == pokemon_name and pkmn.level == lvl and pkmn.gender == gender:
                    pkmn.active = True
                    switch_success = True
                else:
                    pkmn.active = False

            if not switch_success:
                red('Could not find Pokemon %s lvl. %d' % (pokemon_name, lvl))
                red(self.battles[room])
        else:
            # this is the opponent, we can store info on his pokemon
            is_new_pokemon = True
            for pkmn in battle.opponent.pokemon:
                if pkmn.ident == pokemon_name and pkmn.level == lvl and pkmn.gender == gender:
                    pkmn.active = True
                    pkmn.lvl = lvl
                    pkmn.gender = gender
                    pkmn.hp = hp
                    pkmn.status = status
                    is_new_pokemon = False
                else:
                    pkmn.active = False

            if is_new_pokemon:
                battle.opponent.pokemon.append(
                    Pokemon(
                        ident=pokemon_name,
                        name=pokemon_name,
                        level=lvl,
                        gender=gender,
                        hp=hp,
                        active=True,
                        status=status
                    )
                )

    def turn_action(self, room, turn_num):
        # You can let the AI start selection here
        battle = self.battles[room]
        battle.next_turn()
        assert battle.turn == int(turn_num)
        blue_bg(battle.opponent)
        blue_bg(battle.you)
        # self._agent.action(room)

    def move_action(self, room, data):
        # |move|p1a: Empoleon|Stealth Rock|p2a: Raticate
        # glean move information about opponent
        sdata = data.split('|')
        idx, pokemon_name = sdata[0].split(': ')
        idx = idx[:2]
        move = sdata[1]

        battle = self.battles[room]
        if battle.get_player(idx) is battle.opponent:
            green('Opponent pokemon %s can use move "%s"' % (pokemon_name, move))
            pkmn = battle.opponent.get_pokemon('ident', pokemon_name)
            if pkmn:
                pkmn.add_move(move)

    def faint_action(self, room, data):
        # |faint|p1a: Empoleon
        idx, pokemon_name = data.split(': ')
        idx = idx[:2]
        battle = self.battles[room]
        if battle.get_player(idx) is battle.you:
            # AI_SEND_REWARD(BAD)
            red("Oh no your Pokemon: " + pokemon_name + " fainted!")
            # tell AI to switch to another pokemon here
        else:
            # AI_SEND_REWARD(GOOD)
            green("Yes you killed : " + pokemon_name + "!")

    def win_action(self, room, player):
        if player == self.username:
            green("YOU WON! \xF0\x9F\x98\x83")
        else:
            red("YOU LOST! \xF0\x9F\x98\x93")


    def leave_action(self, room, data):
        if data == self.battles[room].opponent.name:
            red("Opponent Left \xF0\x9F\x98\xA2")
            self._agent.forfeit_battle(room)

    # --------- ACTIONS -----------------

    def queryresponse_action(self, room, data):
        query_type, json_data = data.split('|')
        json_data = json.loads(json_data)
        if not json_data:
            json_data = '(Empty)'
        yellow('Query response: ' + query_type + ' JSON: ' + json_data)


    def message_executer(self, conn):
        print 'Message execute process: %d started ' % (os.getpid() if hasattr(os, 'getpid') else 'unknown')
        while True:
            room, message = conn.recv().split(DELIM, 1)

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

                    green('Executing room:' + room + ' op: ' + op + ' data: ' + data)
                    self.execute(room, op, data)
                else:  # should be printed to room log
                    if m[0] == MSG_HEAD:
                        room = m[1:]
                    else:
                        self.log_message('NO ROOM', m)

    def execute(self, room, operation, data):
        if data == '':
            return
        if operation in self._operation_handler:
            self._operation_handler[operation](room, data)
            pass
        else:
            yellow("Unhandled operation: " + operation)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "python stargazer.ShowdownClient [username] [password]"
    freeze_support()
    ps = ShowdownClient(sys.argv[1], sys.argv[2])
    ps.start()
