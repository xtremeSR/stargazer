#! python

'''
    File: Battle.py
    Description: Battle class representing a battle between two players.
'''


class Battle:
    def __init__(
        self,
        resource_uri,
    ):
    '''
        resource_uri (str): The battle resource string given by SHowdown server.
        title (str): The title of the battle.
        format (str): The format of the battle.
        gametype (str): The gametype of the battle.
        generation (str): Pokemon generations included
        rated (boolean): is this battle rated?
        rules (list of str): Each string specifies a rule clause i.e HP Percentage Mod
        _player_1 (Player):  The player object for player 1.
        _player_2 (Player): The player object for player 2.
        _weather (str): The current battle weather.
        _field_effect (str): The current field effect.
        _side_effect (dict mapping player to list): The side effects on each player's side.

    '''
        self.resource_uri = resource_uri
        self.title = None
        self.format = None
        self.gametype = None
        self.generation = None
        self.rated = None
        self.rules = None

        self._player_1 = None
        self._player_2 = None

        self._weather = None
        self._field_effect = None
        self._side_effect = dict()

    def __str__(self):
        pass

    def __repr__(self):
        pass
