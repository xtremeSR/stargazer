#! python

'''
    File: Player.py
    Description: Player class holds details about the
    opposing player
'''


class Pokemon:
    def __init__(
        self,
        name,
        idx
    ):
    """
        name (str): player's name
        idx (str): "p1" or "p2" as assigned to player by pokemon showdown server
        team_size (int): pokemon team size
        ladder_score (int): Optional, ladder score
        pokemon (list of Pokemon): list of pokemon belonging to self.
        available_moves (list of str): list of moves player can use.
    """
        self.name = name
        self.idx = idx
        self.team_size = None
        self.score = None
        self.pokemon = []
        self.available_moves = []

    def __str__(self):
        pass

    def __repr__(self):
        pass

    def get_active_moves(self):
        pass
