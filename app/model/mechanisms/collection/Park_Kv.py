import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Park_Kv(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Park_Kv', suffix='kv', cell=cell)
        self.ion = 'k'
        self.range_params = [
            'gbar',
            'v12',
            'q',
        ]
        self.gbar = 0.0 # S/cm2
        self.Ra = 0.02 # /mV/ms
        self.Rb = 0.006 # /mV/ms
        self.v12 = 25 # mV
        self.q = 9 # mV
        self.temp = 23 # degC
        self.q10 = 2.3 # 1
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "n": {
                "inf": "ninf",
                "tau": "ntau",
                "power": 1
            },
        }

    def rateconst(self, v, r, th, q):
        rateconst = (r * (v - th)) / (1 - np.exp((-((v - th)) / q)))
        return rateconst

    def fakeconst(self, v, r, v12, q):
        conditions = [np.abs(((self.v - self.v12) / self.q)) > 1e-06,
                      ~(np.abs(((self.v - self.v12) / self.q)) > 1e-06)]
        choices = [(r * (v - v12)) / (1 - np.exp((-((v - v12)) / q))),
                   r * q]
        fakeconst = np.select(conditions, choices)
        return fakeconst

    def rates(self, v):
        self.tadj = self.q10 ** ((self.celsius - self.temp) / 10)
        self.alpn = self.rateconst(v, self.Ra, self.v12, self.q)
        self.betn = self.rateconst(v, -(self.Rb), self.v12, -(self.q))
        self.ntau = 1 / (self.tadj * (self.alpn + self.betn))
        self.ninf = self.alpn / (self.alpn + self.betn)

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)
