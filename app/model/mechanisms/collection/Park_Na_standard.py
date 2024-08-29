import numpy as np
try:
    from ..channels import CustomVoltageDependentIonChannel
except:
    from channels import CustomVoltageDependentIonChannel

class Park_Na_standard(CustomVoltageDependentIonChannel):
    def __init__(self, cell=None):
        super().__init__(name='Park_Na_standard', suffix='nas', cell=cell)
        self.ion = 'na'
        self.range_params = [
            'gbar',
            'vhalf_m',
            'sigma_m',
            'k_m',
            'delta_m',
            'tau0_m',
            'vhalf_h',
            'sigma_h',
            'k_h',
            'delta_h',
            'tau0_h',
        ]
        self.gbar = 0.0 # S/cm2
        self.vhalf_m = -32.571 # mV
        self.sigma_m = 9.8 # mV
        self.k_m = 1.884 # 1/ms
        self.delta_m = 0.541 # 1
        self.tau0_m = 0.065 # ms
        self.vhalf_h = -60.0 # mV
        self.sigma_h = -6.2 # mV
        self.k_h = 0.018 # 1/ms
        self.delta_h = 0.397 # 1
        self.tau0_h = 0.795 # ms
        self.temp = 23 # degC
        self.q10 = 2.3 # 1
        self.celsius = 37 # degC
        self.v = np.linspace(-100, 100, 1000)
        self.state_vars = {
            "m": {
                "inf": "m_inf",
                "tau": "tau_m",
                "power": 3
            },
            "h": {
                "inf": "h_inf",
                "tau": "tau_h",
                "power": 1
            },
        }

    def alpha_prime(self, v, k, delta, vhalf, sigma):
        alpha_prime = k * np.exp(((delta * (v - vhalf)) / sigma))
        return alpha_prime

    def beta_prime(self, v, k, delta, vhalf, sigma):
        beta_prime = k * np.exp(((-((1 - delta)) * (v - vhalf)) / sigma))
        return beta_prime

    def rates(self, v):
        self.tadj = self.q10 ** ((self.celsius - self.temp) / 10)
        self.m_inf = 1 / (1 + np.exp((-((v - self.vhalf_m)) / self.sigma_m)))
        self.alpha_m = self.alpha_prime(v, self.k_m, self.delta_m, self.vhalf_m, self.sigma_m)
        self.beta_m = self.beta_prime(v, self.k_m, self.delta_m, self.vhalf_m, self.sigma_m)
        self.tau_m = ((1 / (self.alpha_m + self.beta_m)) + self.tau0_m) / self.tadj
        self.h_inf = 1 / (1 + np.exp((-((v - self.vhalf_h)) / self.sigma_h)))
        self.alpha_h = self.alpha_prime(v, self.k_h, self.delta_h, self.vhalf_h, self.sigma_h)
        self.beta_h = self.beta_prime(v, self.k_h, self.delta_h, self.vhalf_h, self.sigma_h)
        self.tau_h = ((1 / (self.alpha_h + self.beta_h)) + self.tau0_h) / self.tadj

    def update(self, x_range):
        super().update(x_range)
        v = x_range
        self.x_range = x_range
        self.rates(v, )
        self.update_constant_state_vars(x_range)
