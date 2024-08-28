import numpy as np
try:
    from ..channels import CustomCalciumDependentIonChannel
except:
    from channels import CustomCalciumDependentIonChannel

class Poirazi_cal(CustomCalciumDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Poirazi_cal', suffix='cal', cell=cell)
        self.ion = 'ca'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0 # mho/cm2
        self.ki = 0.001 # mM
        self.tfa = 5 # 
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.cai = np.logspace(-5, 5, 1000)
        self.state_vars = {
            "m": {
                "inf": "minf",
                "tau": "taum",
                "power": 1
            },
        }

    def h2(self, cai):
        h2 = self.ki / (self.ki + cai)
        return h2

    def ghk(self, v, ci, co):
        f = self.KTF(self.celsius) / 2
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

    def alpm(self, v):
        alpm = (0.055 * (-(27.01) - v)) / (np.exp(((-(27.01) - v) / 3.8)) - 1)
        return alpm

    def betm(self, v):
        betm = 0.94 * np.exp(((-(63.01) - v) / 17))
        return betm

    def rates(self, v):
        self.a = self.alpm(v)
        self.b = self.betm(v)
        self.minf = self.a / (self.a + self.b)
        self.taum = 1 / (self.tfa * (self.a + self.b))

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)
