#! python

'''
    File: Player.py
    Description: Player class holds details about the
    opposing player
'''
from .utils import string_to_condition

from .Pokemon import Pokemon
from .Move import Move

def json_to_moves(json_move_list):
    assert json_move_list
    result = []
    for move in json_move_list:
        result.append(
            Move(
                move.get("move"),
                int(move.get("pp")) if move.get("pp") else None,
                int(move.get("maxpp")) if move.get("maxpp") else None,
                move.get("target", "normal"),
                move.get("disabled"),
                move.get("id")
            )
        )
    return result

class Player:
    def __init__(self, idx):
        """
            name (str): player's name
            idx (str): "p1" or "p2" as assigned to player by pokemon showdown server
            team_size (int): pokemon team size
            ladder_score (int): Optional, ladder score
            pokemon (list of Pokemon): list of pokemon belonging to self.
            available_moves (list of str): list of moves player can use.
        """
        self.name = None
        self.idx = idx
        self.team_size = None
        self.score = None
        self.pokemon = []
        self.available_moves = []
        self.rqid = None

    def __str__(self):
        return "Name: %s\nTeamsize: %s\n" % (self.name, str(self.team_size)) + \
                '\n'.join([str(pkmn) for pkmn in self.pokemon])

    def __repr__(self):
        pass

    def get_active_moves(self):
        pass

    def update_pokemon(self, pokemon_json):
        # [{"ident":"p2: Mantine","details":"Mantine, L77, F","condition":"257/257","active":true,"stats":{"atk":66,"def":152,"spa":168,"spd":260,"spe":152},"moves":["scald","toxic","roost","airslash"],"baseAbility":"waterabsorb","item":"leftovers","pokeball":"pokeball","ability":"waterabsorb"},{"ident":"p2: Articuno","details":"Articuno, L83","condition":"285/285","active":false,"stats":{"atk":146,"def":214,"spa":205,"spd":255,"spe":189},"moves":["substitute","freezedry","hurricane","roost"],"baseAbility":"pressure","item":"leftovers","pokeball":"pokeball","ability":"pressure"},{"ident":"p2: Zygarde","details":"Zygarde, L73","condition":"278/278","active":false,"stats":{"atk":188,"def":219,"spa":161,"spd":181,"spe":181},"moves":["thousandarrows","outrage","irontail","dragondance"],"baseAbility":"powerconstruct","item":"lumberry","pokeball":"pokeball","ability":"powerconstruct"},{"ident":"p2: Beartic","details":"Beartic, L83, F","condition":"293/293","active":false,"stats":{"atk":263,"def":180,"spa":164,"spd":180,"spe":131},"moves":["aquajet","stoneedge","nightslash","iciclecrash"],"baseAbility":"swiftswim","item":"choiceband","pokeball":"pokeball","ability":"swiftswim"},{"ident":"p2: Torkoal","details":"Torkoal, L79, M","condition":"239/239","active":false,"stats":{"atk":139,"def":267,"spa":180,"spd":156,"spe":77},"moves":["fireblast","earthpower","stealthrock","yawn"],"baseAbility":"drought","item":"leftovers","pokeball":"pokeball","ability":"drought"},{"ident":"p2: Keldeo","details":"Keldeo, L75","condition":"260/260","active":false,"stats":{"atk":113,"def":179,"spa":237,"spd":179,"spe":206},"moves":["substitute","hiddenpowerflying60","scald","secretsword"],"baseAbility":"justified","item":"leftovers","pokeball":"pokeball","ability":"justified"}]
        self.pokemon = []
        for pokemon in pokemon_json:
            ident = pokemon.get("ident")[4:]
            print "pokemon: " + ident
            details = pokemon.get("details", "").split(", ")
            name = details[0] if len(details) else None
            level = int(details[1][1:]) if len(details) > 1 else None
            gender = details[2] if len(details) > 2 else None

            condition = pokemon.get("condition", "")
            hp, status = string_to_condition(condition)

            active = pokemon.get("active", "false") == "true"
            item = pokemon.get("item")
            ability = pokemon.get("ability")
            base_ability = pokemon.get("baseAbility")
            stats = pokemon.get("stats")
            moves = pokemon.get("moves")

            self.pokemon.append(
                Pokemon(
                    ident,
                    name,
                    level,
                    gender,
                    hp,
                    active,
                    item,
                    status,
                    ability,
                    base_ability,
                    stats,
                    moves
                )
            )

    def update_moves(self, moves_json):
        self.available_moves = []
        for pkmn in moves_json:
            move_data = dict()
            move_data["moves"] = json_to_moves(pkmn.get("moves"))
            move_data["canZMove"] = json_to_moves(pkmn.get("canZMove"))
            move_data["canMegaEvo"] = pkmn.get("canMegaEvo", false)
            self.available_moves.append(move_data)

    def update(self, json_data):
        # update pokemon
        # currently active pokemon
        # available moves
        self.update_pokemon(json_data.get("side").get("pokemon"))
        self.rqid = json_data.get("rqid")
        # [{"moves":[{"move":"Scald","id":"scald","pp":24,"maxpp":24,"target":"normal","disabled":false},{"move":"Toxic","id":"toxic","pp":16,"maxpp":16,"target":"normal","disabled":false},{"move":"Roost","id":"roost","pp":16,"maxpp":16,"target":"self","disabled":false},{"move":"Air Slash","id":"airslash","pp":24,"maxpp":24,"target":"any","disabled":false}]}]
        # TODO: make a move class
        self.update_moves(json_data.get("active"))

    def get_pokemon(self, attr, value):
        # return pokemon with pokemon.attr == value
        for pkmn in self.pokemon:
            if pkmn.__getattribute__(attr) == value:
                return pkmn
        return None
