
class Move:
    def __init__(self, name, pp, maxpp, target, disabled=False, idx=None):
        self.name = name
        self.id = idx
        self.pp = pp
        self.maxpp = maxpp
        self.target = "normal"
        self.disabled = disabled

    def is_valid(self):
        return self.maxpp >= self.pp > 0
