#! python

'''
    File: Battle.py
    Description: Battle class representing a battle between two players.
'''
from .Player import Player

class Battle:
    def __init__(self):
        '''
            resource_uri (str): The battle resource string given by SHowdown server.
            title (str): The title of the battle.
            format (str): The format of the battle.
            gametype (str): The gametype of the battle.
            generation (str): Pokemon generations included
            rated (boolean): is this battle rated?
            rules (list of str): Each string specifies a rule clause i.e HP Percentage Mod
            player_1 (Player):  The player object for player 1.
            player_2 (Player): The player object for player 2.
            weather (str): The current battle weather.
            field_effect (str): The current field effect.
            side_effect (dict mapping player to list): The side effects on each player's side.
        '''
        self.resource_uri = None
        self.title = None
        self.format = None
        self.gametype = None
        self.generation = None
        self.rated = None
        self.rules = None

        self.player_1 = None
        self.player_2 = None
        self.you = None
        self.opponent = None

        self.weather = None
        self.field_effect = None
        self.side_effect = {'p1': dict(), 'p2': dict()}
        self.turn = 0

    def __str__(self):
        return """- - - - - - - BATTLE - - - - - - -\nTitle: %s\nResource URI: %s\nFormat: %s\nTurn: %d\n\n--- Player 1 ---\n%s\n--- Player 2 ---\n%s""" % (self.title, self.resource_uri, self.format, self.turn, self.player_1, self.player_2)

    def __repr__(self):
        pass

    def get_player(self, idx):
        if idx == 'p1':
            return self.player_1
        elif idx == 'p2':
            return self.player_2
        else:
            raise ValueError("Incorrect player index: " + idx + " provided.")

    def set_player(self, idx, username):
        if not self.get_player(idx):
            if idx == 'p1':
                self.player_1 = Player(idx)
                self.player_1.name = username
            elif idx == 'p2':
                self.player_2 = Player(idx)
                self.player_2.name = username
            else:
                raise ValueError("Incorrect player index: " + idx + " provided.")

    def next_turn(self):
        self.turn += 1
