import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Park_Ca_LVA(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Park_Ca_LVA', suffix='calva', cell=cell)
        self.ion = 'ca'
        self.range_params = [
            'gbar',
        ]
        self.gbar = 0.0 # S/cm2
        self.v12m = 50 # mV
        self.v12h = 78 # mV
        self.vwm = 7.4 # mV
        self.vwh = 5.0 # mV
        self.am = 3 # ms
        self.ah = 85 # ms
        self.vm1 = 25 # mV
        self.vm2 = 100 # mV
        self.vh1 = 46 # mV
        self.vh2 = 405 # mV
        self.wm1 = 20 # mV
        self.wm2 = 15 # mV
        self.wh1 = 4 # mV
        self.wh2 = 50 # mV
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

    def rates(self, v):
        self.minf = 1.0 / (1 + np.exp((-((v + self.v12m)) / self.vwm)))
        self.hinf = 1.0 / (1 + np.exp(((v + self.v12h) / self.vwh)))
        self.mtau = self.am + (1.0 / (np.exp(((v + self.vm1) / self.wm1)) + np.exp((-((v + self.vm2)) / self.wm2))))
        self.htau = self.ah + (1.0 / (np.exp(((v + self.vh1) / self.wh1)) + np.exp((-((v + self.vh2)) / self.wh2))))

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)
