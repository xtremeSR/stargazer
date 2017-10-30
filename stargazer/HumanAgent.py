import os
import sys

from .Agent import Agent
from .utils import *

class HumanAgent(Agent):
    def __init__(self, ws, client):
        self._ws = ws
        self._client = client

    def start_battle(self):
        green("Starting battle")
        self._ws.write_message('"|/search gen7randombattle"')

    def forfeit_battle(self, room):
        self._ws.write_message('"' + room + '|/forfeit"')
        self._ws.write_message('"|/leave ' + room + '"')

    def choose(self, room, action, items):
        # battle-gen7randombattle-639184562|/choose move 1 zmove|2
        resp = '"' + room + "|/choose " + action + " " + ' '.join(items) + \
         "|" + self._client.battles[room].you['rqid'] + '"'
        #print "<MOVE>"
        #print "<RESPONSE> " + resp
        self._ws.write_message(resp)

    def action(self, room):
        sys.stdin = os.fdopen(0)
        sys.stdout.write("\x1b[5;30;42m>> ")
        command = sys.stdin.readline().strip()
        print '\x1b[0m'
        if command.startswith('forfeit'):
            self.forfeit_battle(room)
        elif command.startswith('move'):
            print '\x1b[0m'
            battle = self._client.battles[room]
            print "Choose your move:"

            # move selected holds strings to send to server
            move_selected = []
            for pkmn_moves in battle.you.available_moves:
                j = 1
                for move in pkmn_moves:
                    if not move.disabled:
                        green(str(j) + '. ' + move.name + " (" + str(move.pp) + "/" + str(move.maxpp) + ")")
                    else:
                         red(str(j) + '. ' + move.name + " (DISABLED)")
                    j += 1
                k = j - 1
                for move in pkmn_moves.get("canZMove"):
                    (str(j) + '. ' + move.name + "\xE2\xAD\x90")
                    j += 1

                sys.stdout.write("\x1b[5;30;42m>> ")
                move_int = int(sys.stdin.readline().strip())
                print '\x1b[0m'
                if move_int > k:
                    move_selected.extend([str(move_int - k), 'zmove'])
                else:
                    move_selected.append(str(move_int))
                if pkmn_moves.get("canMegaEvo"):
                    sys.stdout.write("Do you want to Mega Evolve? [y/N]: ")
                    if sys.stdin.readline().strip().lower() == 'y':
                        move_selected.append('mega')
            self.choose(room, "move", move_selected)
        elif command == 'custom':
            self._ws.write_message(raw_input('\x1b[5;30;42m>> '))
            print '\x1b[0m'
        elif command.startswith('switch'):
            print '\x1b[0m'
            battle = self._client.battles[room]
            print "Which pokemon would you like to switch in?"
            for i, pkmn in enumerate(battle.you.pokemon):
                if pkmn.active:
                    yellow(str(i + 1) + '. ' + str(pkmn))
            sys.stdout.write("\x1b[5;30;42m>> ")
            pokemon_int = sys.stdin.readline().strip()
            self.choose(room, "switch", pokemon_int)
        else:
            red('Bad input!')

        sys.stdin.close()
