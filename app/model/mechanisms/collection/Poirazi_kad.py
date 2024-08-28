import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Poirazi_kad(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_kad', suffix='kad', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0 # mho/cm2
        self.vhalfn = -1 # mV
        self.vhalfl = -56 # mV
        self.a0n = 0.1 # /ms
        self.zetan = -1.8 # 1
        self.zetal = 3 # 1
        self.gmn = 0.39 # 1
        self.gml = 1 # 1
        self.lmin = 2 # mS
        self.nmin = 0.1 # mS
        self.pw = -1 # 1
        self.tq = -40 # 
        self.qq = 5 # 
        self.q10 = 5 # 
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "n": {
                "inf": "ninf",
                "tau": "taun",
                "power": 1
            },
            "l": {
                "inf": "linf",
                "tau": "taul",
                "power": 1
            },
        }

    def alpn(self, v):
        zeta = self.zetan + (self.pw / (1 + np.exp(((v - self.tq) / self.qq))))
        alpn = np.exp(((((0.001 * zeta) * (v - self.vhalfn)) * 96480.0) / (8.315 * (273.16 + self.celsius))))
        return alpn

    def betn(self, v):
        zeta = self.zetan + (self.pw / (1 + np.exp(((v - self.tq) / self.qq))))
        betn = np.exp((((((0.001 * zeta) * self.gmn) * (v - self.vhalfn)) * 96480.0) / (8.315 * (273.16 + self.celsius))))
        return betn

    def alpl(self, v):
        alpl = np.exp(((((0.001 * self.zetal) * (v - self.vhalfl)) * 96480.0) / (8.315 * (273.16 + self.celsius))))
        return alpl

    def betl(self, v):
        betl = np.exp((((((0.001 * self.zetal) * self.gml) * (v - self.vhalfl)) * 96480.0) / (8.315 * (273.16 + self.celsius))))
        return betl

    def rates(self, v):
        self.qt = self.q10 ** ((self.celsius - 24) / 10)
        self.a = self.alpn(v)
        self.ninf = 1 / (1 + self.a)
        self.taun = self.betn(v) / ((self.qt * self.a0n) * (1 + self.a))
        conditions = [self.taun < self.nmin,
                      ~(self.taun < self.nmin)]
        choices = [self.nmin,
                   self.taun]
        self.taun = np.select(conditions, choices)
        self.a = self.alpl(v)
        self.linf = 1 / (1 + self.a)
        self.taul = 0.26 * (v + 50)
        conditions = [self.taul < self.lmin,
                      ~(self.taul < self.lmin)]
        choices = [self.lmin,
                   self.taul]
        self.taul = np.select(conditions, choices)

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)
