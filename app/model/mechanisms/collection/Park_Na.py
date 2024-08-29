import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Park_Na(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Park_Na', suffix='na', cell=cell)
        self.ion = 'na'
        self.range_params = [
            'gbar',
            'v12m',
            'qm',
            'v12ha',
            'v12hb',
            'qh',
            'v12hinf',
            'qhinf',
            'Rma',
            'Rmb',
            'Rhb',
            'Rha',
        ]
        self.gbar = 0.0 # S/cm2
        self.Rma = 0.182 # /mV/ms
        self.Rmb = 0.14 # /mV/ms
        self.v12m = -30 # mV
        self.qm = 9.8 # mV
        self.Rhb = 0.0091 # /mV/ms
        self.Rha = 0.024 # /mV/ms
        self.v12ha = -45 # mV
        self.v12hb = -70 # mV
        self.qh = 5 # mV
        self.v12hinf = -60 # mV
        self.qhinf = 6.2 # mV
        self.temp = 23 # degC
        self.q10 = 2.3 # 1
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "m": {
                "inf": "minf",
                "tau": "mtau",
                "power": 3
            },
            "h": {
                "inf": "hinf",
                "tau": "htau",
                "power": 1
            },
        }

    def rateconst(self, v, r, v12, q):
        conditions = [np.abs(((self.v - v12) / q)) > 1e-06,
                      ~(np.abs(((self.v - v12) / q)) > 1e-06)]
        choices = [(r * (v - v12)) / (1 - np.exp((-((v - v12)) / q))),
                   r * q]
        rateconst = np.select(conditions, choices)
        return rateconst

    def rates(self, v):
        self.tadj = self.q10 ** ((self.celsius - self.temp) / 10)
        self.alpm = self.rateconst(v, self.Rma, self.v12m, self.qm)
        self.betm = self.rateconst(-(v), self.Rmb, -(self.v12m), self.qm)
        self.alph = self.rateconst(v, self.Rha, self.v12ha, self.qh)
        self.beth = self.rateconst(-(v), self.Rhb, -(self.v12hb), self.qh)
        self.mtau = 1 / (self.tadj * (self.alpm + self.betm))
        self.minf = self.alpm / (self.alpm + self.betm)
        self.htau = 1 / (self.tadj * (self.alph + self.beth))
        self.hinf = 1 / (1 + np.exp(((v - self.v12hinf) / self.qhinf)))

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)
