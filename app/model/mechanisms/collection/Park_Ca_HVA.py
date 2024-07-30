import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Park_Ca_HVA(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Park_Ca_HVA', suffix='cahva', cell=cell)
        self.ion = 'ca'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0.0 # S/cm2
        self.Rma = 0.5 # /mV/ms
        self.Rmb = 0.1 # /ms
        self.v12ma = -27 # mV
        self.v12mb = -75 # mV
        self.qma = 3.8 # mV
        self.qmb = 17 # mV
        self.Rha = 0.000457 # /ms
        self.Rhb = 0.0065 # /ms
        self.v12ha = -13 # mV
        self.v12hb = -15 # mV
        self.qha = 50 # mV
        self.qhb = 28 # mV
        self.temp = 23 # degC
        self.q10 = 2.3 # 1
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "m": {
                "inf": "minf",
                "tau": "mtau",
                "power": 2
            },
            "h": {
                "inf": "hinf",
                "tau": "htau",
                "power": 1
            },
        }

    def f_lexp(self, v, R, v12, q):
        dv = -((v - v12))
        f_lexp = (R * dv) / (np.exp((dv / q)) - 1)
        return f_lexp

    def f_exp(self, v, R, v12, q):
        dv = -((v - v12))
        f_exp = R * np.exp((dv / q))
        return f_exp

    def f_sigm(self, v, R, v12, q):
        dv = -((v - v12))
        f_sigm = R / (1 + np.exp((dv / q)))
        return f_sigm

    def rates(self, vm):
        self.tadj = self.q10 ** ((self.celsius - self.temp) / 10)
        self.alpm = self.f_lexp(vm, self.Rma, self.v12ma, self.qma)
        self.betm = self.f_exp(vm, self.Rmb, self.v12mb, self.qmb)
        self.mtau = 1 / (self.tadj * (self.alpm + self.betm))
        self.minf = self.alpm / (self.alpm + self.betm)
        self.alph = self.f_exp(vm, self.Rha, self.v12ha, self.qha)
        self.beth = self.f_sigm(vm, self.Rhb, self.v12hb, self.qhb)
        self.htau = 1 / (self.tadj * (self.alph + self.beth))
        self.hinf = self.alph / (self.alph + self.beth)

    def update(self, x_range):
        super().update(x_range)
        vm = x_range
        self.x_range = x_range
        self.rates(vm, )
        self.update_constant_state_vars(x_range)
