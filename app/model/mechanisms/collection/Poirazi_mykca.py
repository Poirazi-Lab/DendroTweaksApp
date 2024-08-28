import numpy as np
try:
    from ..channels import CustomCalciumDependentIonChannel
except:
    from channels import CustomCalciumDependentIonChannel

class Poirazi_mykca(CustomCalciumDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_mykca', suffix='mykca', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0.0 # mho/cm2
        self.d1 = 0.84 # 
        self.d2 = 1.0 # 
        self.k1 = 0.18 # mM
        self.k2 = 0.011 # mM
        self.bbar = 0.28 # /ms
        self.abar = 0.48 # /ms
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.cai = np.logspace(-5, 5, 1000)
        self.state_vars = {
            "m": {
                "inf": "minf",
                "tau": "mtau",
                "power": 1
            },
        }

    def alp(self, v, ca):
        alp = self.abar / (1 + (self.exp1(self.k1, self.d1, v) / ca))
        return alp

    def bet(self, v, ca):
        bet = self.bbar / (1 + (ca / self.exp1(self.k2, self.d2, v)))
        return bet

    def exp1(self, k, d, v):
        exp1 = k * np.exp((((((-(2) * d) * FARADAY) * v) / R) / (273.15 + self.celsius)))
        return exp1

    def rate(self, v, ca):
        self.a = self.alp(v, ca)
        self.b = self.bet(v, ca)
        self.mtau = 1 / (self.a + self.b)
        self.minf = self.a * self.mtau

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        ca = x_range
        self.x_range = x_range
        self.rate(v, ca, )
        self.update_constant_state_vars(x_range)
