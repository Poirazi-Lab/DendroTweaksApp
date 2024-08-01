import numpy as np
try:
    from ..channels import CustomCalciumDependentIonChannel
except:
    from channels import CustomCalciumDependentIonChannel

class Poirazi_cat(CustomCalciumDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_cat', suffix='cat', cell=cell)
        self.ion = 'ca'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0 # mho/cm2
        self.tBase = 23.5 # degC
        self.ki = 0.001 # mM
        self.tfa = 1 # 
        self.tfi = 0.68 # 
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.cai = np.logspace(-5, 5, 1000)
        self.state_vars = {
            "m": {
                "inf": "minf",
                "tau": "taum",
                "power": 2
            },
            "h": {
                "inf": "hinf",
                "tau": "tauh",
                "power": 1
            },
        }

    def h2(self, cai):
        h2 = self.ki / (self.ki + cai)
        return h2

    def ghk(self, v, ci, co):
        f = self.KTF(celsius) / 2
        nu = v / f
        ghk = (-(f) * (1.0 - ((ci / co) * np.exp(nu)))) * self.efun(nu)
        return ghk

    def KTF(self, celsius):
        KTF = (25.0 / 293.15) * (celsius + 273.15)
        return KTF

    def efun(self, z):
        conditions = [np.abs(z) < 0.0001,
                      ~(np.abs(z) < 0.0001)]
        choices = [1 - (z / 2),
                   z / (np.exp(z) - 1)]
        efun = np.select(conditions, choices)
        return efun

    def alph(self, v):
        alph = 0.00016 * np.exp((-((v + 57)) / 19))
        return alph

    def beth(self, v):
        beth = 1 / (np.exp(((-(v) + 15) / 10)) + 1.0)
        return beth

    def alpm(self, v):
        alpm = (0.1967 * ((-(1.0) * v) + 19.88)) / (np.exp((((-(1.0) * v) + 19.88) / 10.0)) - 1.0)
        return alpm

    def betm(self, v):
        betm = 0.046 * np.exp((-(v) / 22.73))
        return betm

    def rates(self, v):
        self.a = self.alpm(v)
        self.taum = 1 / (self.tfa * (self.a + self.betm(v)))
        self.minf = self.a / (self.a + self.betm(v))
        self.a = self.alph(v)
        self.tauh = 1 / (self.tfi * (self.a + self.beth(v)))
        self.hinf = self.a / (self.a + self.beth(v))

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)
