#! python

'''
    File: Pokemon.py
    Description: Pokemon class encapsulates pokemon attributes
    such as health, status etc. along with pokemon behavior
    such as mega-evolving.
'''


class Pokemon:
    def __init__(
        self,
        ident,
        name,
        level,
        gender,
        hp,
        active=False,
        item=None,
        status=None,
        ability=None,
        base_ability=None,
        stats=None,
        moves=None,
    ):
        '''
            name (str): pokemon name
            level (int): pokemon level, max 100
            gender (str): "M", "F" or ""
            hp (float): 0 <= hp <= 1
            active (bool): is pokemon on field?
            item (str): held item
            status (str): current effect, ie. confused, poisoned etc.
            ability (str): pokemon's ability
            base_ability (str): pokemon's base ability, in case of ability shenanigans
            stats (dict): dictionary of str -> int, mapping status to 8 bit ints
            moves (list of str) known moves
        '''
        self.ident = ident
        self.name = name
        self.level = level
        self.gender = gender
        self.hp = hp
        self.active = active
        self.item = item
        self.status = status
        self.ability = ability
        self.base_ability = base_ability
        self.stats = stats if stats else dict()
        self.moves = moves if moves else []
        self.boost = dict()

    def __str__(self):
        active = "[ACTIVE]" if self.active else ""
        return "%s %s lvl. %d %s hp (%f/1.0)" % (active, self.name, self.level, self.gender, self.hp) + \
        " " + ' '.join([move for move in  self.moves])

    def __repr__(self):
        pass

    def boost(attr, value):
        self.boost[attr] = self.boost.get(attr, 0) + value

    def add_move(move):
        if move not in self.moves:
            self.moves.append(move)
