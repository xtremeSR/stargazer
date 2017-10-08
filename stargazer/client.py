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

def red(string):
    print '\x1b[1;31;40m%s\x1b[0m' % string

def green(string):
    print '\x1b[1;32;40m%s\x1b[0m' % string

def green_bg(string):
    print '\x1b[5;30;42m%s\x1b[0m' % string

def white_bg(string):
    print '\x1b[0;30;47m%s\x1b[0m' % string

def blue_bg(string):
    print '\x1b[0;30;44m%s\x1b[0m' % string

def yellow(string):
    print '\x1b[1;33;40m%s\x1b[0m' % string

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
            'title': self.title_action,
            'updatesearch': self.updatesearch_action,
            #'updatechallenges': self.updatechallenges_action,
            'queryresponse': self.queryresponse_action,
            'updateuser': self.updateuser_action,
            'challstr': self.challstr_action,
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
            '-weather': self.weather_action,
            '-status': self.status_action,
            '-ability': self.ability_action,
            '-drag': self.drag_action,
            #'-supereffective': self.supereffective_action,
            #'-resisted': self.resisted_action,
            #'-immune': sel.immune_action,
            '-damage': self.damage_action,
            '-fail': self.fail_action,

            'teamsize': self.teamsize_action,
            #'cant': self.cant_action,
            #'miss': self.miss_action,
            'player': self.player_action,
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

        self.ioloop = IOLoop.instance()
        self.connect()
        # PeriodicCallback(self.keep_alive, 20000, io_loop=self.ioloop).start()
        self.ioloop.start()

    # ------------ corountines -----------------------
    @gen.coroutine
    def connect(self):
        self.generate_URL()
        print 'Opening Websocket to ' + self.url
        try:
            self.ws = yield websocket_connect(self.url, ping_interval=3, ping_timeout=30)
        except Exception, e:
            red("Could not connect to Showdown")
            red(e.strerror)
        else:
            green("Websocket connected")
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
                    green("Websocket connection closed.")
                self.ws = None
                self.username = None
                break
            else:
                self.parse_message(msg)


    # ----------- client to server functions ---------
    def send_command_to_showdown(self):
        while True:
            raw_input()
            with self.terminal_lock:
                command = raw_input("\x1b[5;30;42m>> ").strip()
                print '\x1b[0m'
                if command == 'start':
                    self.init_battle()
                elif command.startswith('forfeit'):
                    if len(self.battles):
                        print "Which battle would you like to forfeit?"
                        for i in range(len(self.battles)):
                            white_bg(str(i) + '. ' + self.battles[i])
                        inp = raw_input('\x1b[5;30;42m>> ').strip()
                        if inp == 'q':
                            continue
                        battle_num = int(inp)
                        if 0 <= battle_num < len(self.battles):
                            self.forfeit_battle(self.battles[battle_num])
                    else:
                        red("Error: There are no current active battles")
                elif command.startswith('move'):
                    print "Which battle would you like to move in?"
                    for i in range(len(self.battles)):
                        white_bg(str(i) + '. ' + self.battles[i])
                    inp = raw_input('\x1b[5;30;42m>> ').strip()
                    if inp == 'q':
                        continue
                    battle_num = int(inp)
                    print '\x1b[0m'
                    battle = self.battleState[self.battles[battle_num]]
                    print "Choose your move:"
                    move_selected = []
                    for pokemon in battle[battle['you']]['active']:
                        for j in range(len(pokemon["moves"])):
                            move = pokemon['moves'][j]
                            if not move['disabled']:
                                yellow(str(j + 1) + '. ' + move["move"] + " (" + str(move["pp"]) + "/" + str(move["maxpp"]) + ")")
                            else:
                                 red(str(j + 1) + '. ' + move["move"] + " (DISABLED)")
                        if "canZMove" in pokemon:
                            for j in range(len(pokemon["canZMove"])):
                                move = pokemon['canZMove'][j]
                                yellow(str(j + 5) + '. ' + move["move"] + "\xE2\xAD\x90")
                        move_int = int(raw_input("\x1b[5;30;42m>> "))
                        print '\x1b[0m'
                        if move_int > 4:
                            move_selected.extend([str(move_int - 4), 'zmove'])
                        else:
                            move_selected.append(str(move_int))
                        if "canMegaEvo" in pokemon:
                            if (raw_input("Do you want to Mega Evolve? [y/N]: ") == 'y'):
                                move_selected.append('mega')
                    self.choose(self.battles[battle_num], "move", move_selected)
                elif command.startswith('switch'):
                    print "Which battle would you like to switch in?"
                    for i in range(len(self.battles)):
                        white_bg(str(i) + '. ' + self.battles[i])
                    inp = raw_input("\x1b[5;30;42m>> ").strip()
                    if inp == 'q':
                        continue
                    battle_num = int(inp)
                    print '\x1b[0m'
                    battle = self.battleState[self.battles[battle_num]]
                    print "Which pokemon would you like to switch to?"
                    for i in range(len(battle[battle['you']]['pokemon'])):
                        pokemon = battle[battle['you']]['pokemon'][i]
                        if not pokemon['active']:
                            yellow(str(i + 1) + '. ' + pokemon['details'])
                    pokemon_int = raw_input("\x1b[5;30;42m>> ")
                    if pokemon_int == 'q':
                        continue
                    self.choose(self.battles[battle_num], "switch", pokemon_int)
                elif command.startswith('pdb'):
                    pdb.set_trace()
                elif command == 'custom':
                    self.ws.write_message(raw_input('\x1b[5;30;42m>> '))
                    print '\x1b[0m'
                else:
                    red('Bad input!')


    def choose(self, room, action, items):
        # battle-gen7randombattle-639184562|/choose move 1 zmove|2
        resp = '"' + room + "|/choose " + action + " " + ' '.join(items) + "|" + self.battleState[room][self.battleState[room]['you']]['rqid'] + '"'
        #print "<MOVE>"
        #print "<RESPONSE> " + resp
        self.ws.write_message(resp)


    def parse_message(self, message):
        room = None
        message = message.decode('unicode_escape')
        content_match = re.match('a\["(.*)"\]', message, flags=re.DOTALL)
        if not content_match:
            self.log_message('BAD FORMAT', message)
            return
        m_data = content_match.group(1)
        with self.terminal_lock:
            green(m_data)
        message_lines = m_data.split('\n')

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

                yellow('Executing op: ' + op + ' data: ' + data)
                self.execute(room, op, data)
            else:  # should be printed to room log
                if m[0] == '>':
                    room = m[1:]
                else:
                    self.log_message('NO ROOM', m)

    def execute(self, room, operation, data):
        if data == '':
            return
        if operation in self.operation_handler:
            self.operation_handler[operation](room, data)
        else:
            with self.terminal_lock:
                red("Unhandled op: " + operation)

    def join_action(self, room, data):
        if not room:
            room = 'None'
        with self.terminal_lock:
            blue_bg(data + ' joined ' + room)

    def leave_action(self, room, data):
        if data == self.battleState[room][self.battleState[room]['opponent']]['name']:
            with self.terminal_lock:
                red("Opponent Left \xF0\x9F\x98\xA2")
            self.forfeit_battle(room)

    def chat_action(self, room, data):
        if not room:
            room = 'None'
        with self.terminal_lock:
            blue_bg(room + ': ' + data)

    def log_message(self, room, message):
        with self.terminal_lock:
            yellow("LOG: " + room + ': ' + message)

    def updateuser_action(self, room, data):
        self.playername, loggedin, self.avatar = data.split('|')
        self.loggedin = (loggedin == '1')
        with self.terminal_lock:
            print "Updating User"
            print "Player: " + self.playername
            print ("Logged in" if self.loggedin else "Not logged in")

    # ------------ handlers ------------------------

    def boost_action(self, room, data):
        # |-boost|p1a: Tornadus|atk|1
        # |-boost|p1a: Houndoom|spa|2
        # |-boost|p2a: Serperior|spa|2
        pokemon_data, boost_attr, boost_val = data.split('|')
        player_token, pokemon_name = pokemon_data.split(': ')
        player_token = player_token[:2]
        for pokemon in self.battleState[room][player_token]['pokemon']:
            if pokemon['ident'] == player_token + ': ' + pokemon_name:
                if 'boost' not in pokemon:
                    pokemon['boost'] = dict()
                if boost_attr not in pokemon['boost']:
                    pokemon['boost'][boost_attr] = 0
                pokemon['boost'][boost_attr] += int(boost_val)
                break



    def unboost_action(self, room, data):
        # |-unboost|p2a: Manectric|atk|1
        #|-unboost|p2a: Simisage|atk|1
        #|-unboost|p1a: Lumineon|atk|1
        pokemon_data, boost_attr, boost_val = data.split('|')
        player_token, pokemon_name = pokemon_data.split(': ')
        player_token = player_token[:2]
        for pokemon in self.battleState[room][player_token]['pokemon']:
            if pokemon['ident'] == player_token + ': ' + pokemon_name:
                if 'boost' not in pokemon:
                    pokemon['boost'] = dict()
                if boost_attr not in pokemon['boost']:
                    pokemon['boost'][boost_attr] = 0
                pokemon['boost'][boost_attr] += -int(boost_val)
                break

    def crit_action(self, room, data):
        # |-crit|p1a: Sharpedo
        # if you bad
        pass

    def detailschange_action(self, room, data):
        # |detailschange|p1a: Swampert|Swampert-Mega, L75, F
        # |detailschange|p1a: Gardevoir|Gardevoir-Mega, L77, F
        pass


    def switch_action(self, room, data):
        # |switch|p2a: Porygon2|Porygon2, L79|100/100
        # this and drag is only place where you can gain information about the opponent's pokemon
        pokemon, details, condition = data.split('|')
        player_token, pokemon_name = pokemon.split(':')
        player_token = player_token[:2]
        pokemon_name = pokemon_name.strip()

        if player_token == self.battleState[room]['you']:
            switch_success = False
            for pokemon in self.battleState[room][player_token]["pokemon"]:
                if pokemon['details'] == details:
                    pokemon['active'] = True
                    switch_success = True
                else:
                    pokemon['active'] = False

            if not switch_success:
                red('Could not find Pokemon: ' + details)
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
                        'item': None,
                        'details': details,
                        'active': True,
                        'moves': [],
                        'condition': condition
                    }
                )

    def fieldstart_action(self, room, data):
        # |-fieldstart|move: Misty Terrain|[from] ability: Misty Surge|[of] p2a: Tapu Fini

        # TODO: get ability of opponent from this
        field_info = data.split('|')
        field_name = field_info[0]
        with self.terminal_lock:
            print 'Field effect: ' + field_name
        self.battleState[room]['field'] = field_name

    def fieldend_action(self, room, data):
        # |-fieldend|Misty Terrain
        field_info = data.split('|')
        field_name = field_info[0]
        with self.terminal_lock:
            print 'Field effect: ' + field_name
        self.battleState[room]['field'] = field_name
        pass

    def heal_action(self, room, data):
        #p1a: Bronzong|93/100 brn|[from] item: Leftovers
        #p2a: Moltres|252/271|[from] item: Leftovers
        #p2a: Articuno|69/100|[from] item: Leftovers
        # we can glean information of opponent's item
        data = data.split('|')
        player_token = data[0][:2]
        condition = data[1]
        pokemon_name = data[0][5:]

        if player_token == self.battleState[room]['opponent']:
            for pokemon in self.battleState[room][player_token]['pokemon']:
                if pokemon['ident'] == player_token + ': ' + pokemon_name:
                    if len(data) == 3:
                        item = data[2].split(': ')[1]
                        with self.terminal_lock:
                            green('Opponents ' + pokemon_name + ' holds a ' + item)
                        pokemon['item'] = item
                    pokemon['condition'] = condition
                    break

    def status_action(self, room, data):
        # |-status|p1a: Lunatone|brn
        # |-status|p1a: Bronzong|brn|[from] ability: Flame Body|[of] p2a: Moltres
        # p2a: Bouffalant|tox
        # we can glean ability of opponent's pokemon
        sdata = data.split('|')
        player_token = sdata[0][:2]
        status = sdata[1]
        pokemon_name = sdata[0][5:]
        opponent_content = re.match("ability:\s+?(.+?)\|\[of\] " + self.battleState[room]['opponent'] + "a: (.+)", data)
        if (player_token == self.battleState[room]['opponent']) or opponent_content:
            ability = None
            if opponent_content:
                player_token = self.battleState[room]['opponent']
                ability = opponent_content.group(1)
                pokemon_name = player_token + ': ' + opponent_content.group(2)
                with self.terminal_lock:
                    green("Opponents %s ability is %s" % (pokemon_name, ability))
            for pokemon in self.battleState[room][player_token]['pokemon']:
                if pokemon['ident'] == player_token + ': ' + pokemon_name:
                    if ability:
                        pokemon['ability'] = ability
                    else:
                        # add pokemon condition to opponent's pokemon
                        pokemon['condition'] = pokemon['condition'].split()[0] + ' ' + status
                    break


    def weather_action(self, room, data):
        # |-weather|SunnyDay|[upkeep]
        # |-weather|SunnyDay|[upkeep]
        # |-weather|none
        # |-weather| data: Sandstorm|[from] ability: Sand Stream|[of] p2a: Tyranitar
        # |-weather|RainDance|[from] ability: Drizzle|[of] p2a: Kyogre
        # TODO: scrape ability of pokemon
        if data == 'none':
            self.battleState[room]['weather'] = None
        else:
            sdata = data.split('|')
            self.battleState[room]['weather'] = sdata[0]
            player_token = self.battleState[room]['opponent']
            if player_token in data:
                pokemon_name = self.battleState[room]['opponent'] + ': ' + sdata[2].split(':')[1]
                for pokemon in self.battleState[room][self.battleState[room]['opponent']]['pokemon']:
                    if pokemon['ident'] == player_token + ': ' + pokemon_name:
                        if 'ability'in sdata[1]:
                            pokemon['ability'] = sdata[1].split(': ')[1]
                        break

    def win_action(self, room, data):
        if room in self.battles:
            with self.terminal_lock:
                if data == 'Sooham Rafiz':
                    green("YOU WON! \xF0\x9F\x98\x83")
                else:
                    red("YOU LOST! \xF0\x9F\x98\x93")

    def turn_action(self, room, data):
        # You can let the AI start selection here
        self.battleState[room]['turn'] = int(data)
        with self.terminal_lock:
            white_bg('TURN ' + data)
            for pokemon in self.battleState[room][self.battleState[room]['opponent']]['pokemon']:
                blue_bg('Pkmn: %s, HP: %s, item: %s, ability: %s -- %s' % (pokemon['ident'][4:], pokemon['condition'], pokemon['item'], pokemon['ability'], pokemon['moves']))

    def init_action(self, room, data):
        # |init|battle
        if data == 'battle':
            self.battleState[room] = dict()
            self.battleState[room]['p1'] = dict()
            self.battleState[room]['p2'] = dict()

    def player_action(self, room, data):
        # |player|p1|Sooham Rafiz|102
        if room in self.battles:
            player_token, player_name, _ = data.split('|')
            self.battleState[room][player_token]['name'] = player_name
            if player_name == 'Sooham Rafiz':
                self.battleState[room]['you'] = player_token
            else:
                self.battleState[room]['opponent'] = player_token

    def teamsize_action(self, room, data):
        # |teamsize|p1|6
        player_token, teamsize = data.split('|')
        self.battleState[room][player_token]['teamsize'] = int(teamsize)

    def request_action(self, room, data):
        # {"active":[{"moves":[{"move":"Thunderbolt","id":"thunderbolt","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Focus Blast","id":"focusblast","pp":8,"maxpp":8,"target":"normal","disabled":false},{"move":"Nasty Plot","id":"nastyplot","pp":32,"maxpp":32,"target":"self","disabled":false},{"move":"Surf","id":"surf","pp":24,"maxpp":24,"target":"allAdjacent","disabled":false}],"canZMove":[{"move":"Stoked Sparksurfer","target":"normal"},null,null,null]}],"side":{"name":"Sooham Rafiz","id":"p1","pokemon":[{"ident":"p1: Raichu","details":"Raichu-Alola, L83, M","condition":"235/235","active":true,"stats":{"atk":146,"def":131,"spa":205,"spd":189,"spe":230},"moves":["thunderbolt","focusblast","nastyplot","surf"],"baseAbility":"surgesurfer","item":"aloraichiumz","pokeball":"pokeball","ability":"surgesurfer"},{"ident":"p1: Xurkitree","details":"Xurkitree, L76","condition":"251/251","active":false,"stats":{"atk":140,"def":152,"spa":307,"spd":152,"spe":170},"moves":["energyball","dazzlinggleam","voltswitch","thunderbolt"],"baseAbility":"beastboost","item":"choicescarf","pokeball":"pokeball","ability":"beastboost"},{"ident":"p1: Terrakion","details":"Terrakion, L77","condition":"267/267","active":false,"stats":{"atk":243,"def":183,"spa":155,"spd":183,"spe":211},"moves":["swordsdance","earthquake","closecombat","stoneedge"],"baseAbility":"justified","item":"lifeorb","pokeball":"pokeball","ability":"justified"},{"ident":"p1: Kartana","details":"Kartana, L75","condition":"212/212","active":false,"stats":{"atk":315,"def":240,"spa":132,"spd":90,"spe":207},"moves":["leafblade","sacredsword","swordsdance","psychocut"],"baseAbility":"beastboost","item":"lifeorb","pokeball":"pokeball","ability":"beastboost"},{"ident":"p1: Braviary","details":"Braviary, L81, M","condition":"295/295","active":false,"stats":{"atk":246,"def":168,"spa":139,"spd":168,"spe":176},"moves":["return","bulkup","superpower","substitute"],"baseAbility":"defiant","item":"leftovers","pokeball":"pokeball","ability":"defiant"},{"ident":"p1: Comfey","details":"Comfey, L79, M","condition":"210/210","active":false,"stats":{"atk":128,"def":188,"spa":175,"spd":219,"spe":204},"moves":["toxic","aromatherapy","uturn","synthesis"],"baseAbility":"naturalcure","item":"leftovers","pokeball":"pokeball","ability":"naturalcure"}]},"rqid":2}
        pokemon_data = json.loads(data)

        player_token = pokemon_data["side"]["id"]

        if 'pokemon' not in self.battleState[room][player_token]:
            self.battleState[room][player_token]["pokemon"] = pokemon_data["side"]["pokemon"]
        else:
            for i in range(len(pokemon_data["side"]["pokemon"])):
                self.battleState[room][player_token]['pokemon'][i]['details'] = pokemon_data['side']['pokemon'][i]['details']
                self.battleState[room][player_token]['pokemon'][i]['condition'] = pokemon_data['side']['pokemon'][i]['condition']
                self.battleState[room][player_token]['pokemon'][i]['active'] = pokemon_data['side']['pokemon'][i]['active']
                self.battleState[room][player_token]['pokemon'][i]['stats'] = pokemon_data['side']['pokemon'][i]['stats']
                self.battleState[room][player_token]['pokemon'][i]['moves'] = pokemon_data['side']['pokemon'][i]['moves'][:]
                self.battleState[room][player_token]['pokemon'][i]['baseAbility'] = pokemon_data['side']['pokemon'][i]['baseAbility']
                self.battleState[room][player_token]['pokemon'][i]['item'] = pokemon_data['side']['pokemon'][i]['item']
                self.battleState[room][player_token]['pokemon'][i]['pokeball'] = pokemon_data['side']['pokemon'][i]['pokeball']
                self.battleState[room][player_token]['pokemon'][i]['ability'] = pokemon_data['side']['pokemon'][i]['ability']

        self.battleState[room][player_token]["rqid"] = str(pokemon_data["rqid"])
        if 'active' in pokemon_data:
            self.battleState[room][player_token]["active"] = pokemon_data["active"]

    def start_action(self, room, data):
        # |-start|p2a: Emolga|Substitute
        #|-start|p2a: Tapu Fini|Substitute
        pass

    def end_action(self, room, data):
        # |-end|p1a: Regigigas|Slow Start|[silent]
        pass

    def activate_action(self, room, data):
        # |-activate|p1a: Registeel|move: Protect
        # |-activate|p2a: Comfey|move: Aromatherapy
        # |-activate|p2a: Tapu Fini|move: Misty Terrain

        pass

    def damage_action(self, room, data):
        # p2a: Vespiquen|0 fnt
        # p1a: Bronzong|87/100 brn|[from] brn
        # |-damage|p1a: Lanturn|225/343
        # |-damage|p2a: Emboar|88/100|[from] Recoil|[of] p1a: Lanturn
        # |-damage|p2a: Raticate|26/100|[from] item: Life Orb
        # |-damage|p2a: Yanmega|74/100 psn|[from] psn
        # TODO: you can get item information from this
        damage_info = data.split('|')
        player_token = damage_info[0][:2]
        pokemon_name = damage_info[0][5:]
        condition = damage_info[1]

        if player_token == self.battleState[room]['opponent']:
            for pokemon in self.battleState[room][player_token]['pokemon']:
                if pokemon['ident'] == player_token + ': ' + pokemon_name:
                    if len(data) == 3 and ('item' in data[2]):
                        item = ''.join((((data[2]).split(': '))[1]).split()).lower()
                        pokemon['item'] = item
                    pokemon['condition'] = condition
                    break


    def fail_action(self, room, data):
        #|-fail|p2a: Raticate
        # -fail| p2a: Solgaleo|unboost|[from] ability: Full Metal Body|[of] p2a: Solgaleo
        sdata = data.split('|')
        player_token = sdata[0][:2]
        if player_token == self.battleState[room]['you']:
            # AI_SEND_REWARD(BAD)
            with self.terminal_lock:
                red("Your pokemon failed to move: " + pokemon)
            # tell AI to switch to another pokemon here
        else:
            # AI_SEND_REWARD(GOOD)
            with self.terminal_lock:
                green("Opponent's pokemon failed to move: " + pokemon)

    def immune_action(self, room, data):
        #|-immune|p1a: Muk|[msg]
        #|-immune|p2a: Solgaleo|[msg]
        player_token, pokemon = data.split('|')[0].split(': ')
        player_token = player_token[:2]
        if player_token == self.battleState[room]['you']:
            # AI_SEND_REWARD(GOOD)
            with self.terminal_lock:
                green("Your pokemon was immune: " + pokemon)
            # tell AI to switch to another pokemon here
        else:
            # AI_SEND_REWARD(BAD)
            with self.terminal_lock:
                red("Opponent's pokemon was immune: " + pokemon)

    def item_action(self, room, data):
        # |-item|p2a: Carracosta|Air Balloon
        pokemon_data, item = data.split('|')
        player_token, pokemon_name = pokemon_data.split(': ')
        player_token = player_token[:2]

        if player_token == self.battleState[room]['opponent']:
            for pokemon in self.battleState[room][player_token]['pokemon']:
                if pokemon['ident'] == player_token + ': ' + pokemon_name:
                    pokemon['item'] = item
                    break

    def enditem_action(self, room, data):
        # |-enditem|p2a: Carracosta|Air Balloon
        # |-enditem|p1a: Dragonite|Lum Berry|[eat]
        # |-enditem|p1a: Furfrou|Chesto Berry|[from] move: Knock Off|[of] p2a: Simisage
        sdata = data.split('|')
        player_token, pokemon_name = sdata[0].split(': ')
        player_token = player_token[:2]
        item = sdata[1]

        if player_token == self.battleState[room]['opponent']:
            for pokemon in self.battleState[room][player_token]['pokemon']:
                if pokemon['ident'] == player_token + ': ' + pokemon_name:
                    pokemon['item'] = None
                    break

    def sidestart_action(self, room, data):
        #|-sidestart|p1: u05431ujijklk|Spikes
        #-sidestart|p1: Sooham Rafiz|move: Stealth Rock
        #|-sidestart|p2: Zsguita|move: Stealth Rock
        player, side_effect = data.split('|')
        side_name = side_effect[1][6:]
        player_token = player[:2]

        with self.terminal_lock:
            print 'Side effect on player ' + player_token + "'s side: " + side_name
        if 'side' not in self.battleState[room][player_token]:
            self.battleState[room][player_token]['side'] = []
            self.battleState[room][player_token]['side'].append(side_name)

    def sideend_action(self, room, data):
        pass

    def move_action(self, room, data):
        # |move|p1a: Empoleon|Stealth Rock|p2a: Raticate
        # glean move information about opponent
        player_token, pokemon_name = data.split('|')[0].split(': ')
        player_token = player_token[:2]
        move = ''.join(data.split('|')[1].lower().split(' '))

        if player_token == self.battleState[room]['opponent']:
            with self.terminal_lock:
                green('Opponent pokemon %s can use move %s' % (pokemon_name, move))
            for pokemon in self.battleState[room][player_token]['pokemon']:
                if pokemon['ident'] == player_token + ': ' + pokemon_name:
                    if move not in pokemon['moves']:
                        pokemon['moves'].append(move)
                    break

    def faint_action(self, room, data):
        # |faint|p1a: Empoleon
        player_token, pokemon = data.split(': ')
        player_token = player_token[:2]
        with self.terminal_lock:
            if player_token == self.battleState[room]['you']:
                # AI_SEND_REWARD(BAD)
                red("Oh no your Pokemon: " + pokemon + " fainted!")
                # tell AI to switch to another pokemon here
            else:
                # AI_SEND_REWARD(GOOD)
                green("Yes you killed : " + pokemon + "!")

    def resisted_action(self, room, data):
        # |-resisted|p1a: Lanturn
        # |-resisted|p1a: Lunatone
        # if player is you
        # AI_SEND_REWARD(GOOD)
        # else
        # AI_SEND_REWARD(BAD)
        pass


    def supereffective_action(self, room, data):
        #|-supereffective|p1a: Muk
        # if player is opponent
        # AI_SEND_REWARD(GOOD)
        # else
        # AI_SEND_REWARD(BAD)
        pass

    def cant_action(self, room, data):
        #| cant |p2a: Klefki|par
        pass

    def miss_action(self, room, data):
        # |-miss|p2a: Klefki|p1a: Qwilfish
        # |-miss|p2a: Talonflame|p1a: Lunatone
        pass

    def drag_action(self, room, data):
        # |drag|p1a: Comfey|Comfey, L79, M|210/210
        self.switch(room, data)

    def ability_action(self, room, data):
        # |-ability|p1a: Landorus|Intimidate|boost
        data = data.split('|')
        player_token, pokemon_name = data[0].split(': ')
        ability = data[1]
        player_token = player_token[:2]

        if player_token == self.battleState[room]['opponent']:
            with self.terminal_lock:
                green('Found opponent\'s ' + pokemon_name + ' ability is ' + ability)
            for pokemon in self.battleState[room][player_token]['pokemon']:
                if pokemon['ident'] == player_token + ': ' + pokemon_name:
                    pokemon['ability'] = ability
                    break


    # ----- Pokemon Showdown interface actions -----
    def init_battle(self):
        self.ws.write_message('"|/search gen7randombattle"')

    def forfeit_battle(self, battle_room):
        self.ws.write_message('"' + battle_room + '|/forfeit"')
        self.ws.write_message('"|/leave ' + battle_room + '"')

    def title_action(self, room, data):
        if self.battleState[room]:
            self.battleState[room]['title'] = data

    def formats_action(self, room, data):
        return
        with self.terminal_lock:
            print '\n'.join(["<FORMAT>: " + d for d in data.split(',')])

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
        print "Logging in..."
        resp = requests.post('https://play.pokemonshowdown.com/action.php', data=payload)
        if (resp.status_code == 200):
            # with self.terminal_lock:
            self.ws.write_message('"|/trn ' + ','.join(["Sooham Rafiz", '0', json.loads(resp.text[1:])['assertion']]) + '"')
        else:
            with self.terminal_lock:
                red('Error: challstr response not 200')

    def queryresponse_action(self, room, data):
        query_type, json_data = data.split('|')
        json_data = json.loads(json_data)
        if not json_data:
            json_data = '(Empty)'
        with self.terminal_lock:
            yellow('Query response: ' + query_type + ' JSON: ' + json_data)

    def updatesearch_action(self, room, data):
        # |updatesearch|{"searching":[],"games":{"battle-gen7ubers-640967362":"[Gen 7] Ubers Battle*"}}
        # |updatesearch|{"searching":["gen7ubers"],"games":null}
        battles = json.loads(data)
        current_games = battles['games']
        with self.terminal_lock:
            print "Looking for %d battles, playing %d" % (len(battles['searching']), len(current_games) if current_games else 0)
        self.battles = current_games.keys() if current_games else []

    def generate_URL(self):
        c = lambda s, i: s + chr(i)
        name = reduce(c, random.sample(self.chars, 8), '')

        self.username = name
        self.token = str(random.randint(0, 1000))
        self.url = '/'.join([self.base, self.token, self.username, 'websocket'])

    # --- unimplemented actions ----
    def nametaken_action(self, room, data):
        pass

    def updatechallenges_action(self, room, data):
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
