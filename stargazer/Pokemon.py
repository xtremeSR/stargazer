#! python

'''
    File: Pokemon.py
    Description: Pokemon class encapsulates pokemon attributes
    such as health, status etc. along with pokemon behavior
    such as mega-evolving.
'''


class Pokemon(object):
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
        assert type(ident) in [str, unicode]
        assert type(name) in [str, unicode]
        assert type(level) == int and (0 < level <= 100)
        assert gender in ['M', 'F', None]
        assert type(hp) == float and (0.0 <= hp <= 1.0)
        if active != None:
            assert type(active) in [bool, int]
        if item != None:
            assert type(item) in [str, unicode]
        if status != None:
            assert type(status) in [str, unicode]
        if ability != None:
            assert type(ability) in [str, unicode]
        if base_ability != None:
            assert type(base_ability) in [str, unicode]
        if stats != None:
            assert type(stats) == dict
        if moves != None:
            assert type(moves) == list

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
        self._boost = dict()

    def __str__(self):
        return "Active: %s\nId: %s\nName: %s\nLvl. %d\nGender: %s\nHP: %.2f\nItem: %s\nStatus: %s\nAbility: %s\nBase ability: %s\n" % (self.active, self.ident, self.name, self.level, self.gender, self.hp, self.item, self.status, self.ability, self.base_ability) \
        + '\n'.join(["Move %d: %s" % (i+1, move) for i, move in enumerate(self.moves)]) + '\n' \
        + '\n'.join([attr + " boosted " + str(boost) for attr, boost in self._boost.items()])

    def boost(self, attr, value):
        self._boost[attr] = self._boost.get(attr, 0) + value

    def unboost(self, attr, value):
        self._boost[attr] = self._boost.get(attr, 0) - value

    def add_move(self, move):
        if move not in self.moves:
            self.moves.append(move)
