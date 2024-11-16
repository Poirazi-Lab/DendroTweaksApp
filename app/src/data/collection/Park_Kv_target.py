# This Python channel class was automatically generated from a MOD file
# using DendroTweaks toolbox, dendrotweaks.dendrites.gr

from dendrotweaks.mechanisms.mechanisms import CustomIonChannel
# from jaxley.solver_gate import exponential_euler
import numpy as np


class Kv(CustomIonChannel):
    """
    Kv_Park_ref
    """

    def __init__(self, name="Kv"):
        super().__init__(name=name)
        self.channel_params = {
            "Kv_gbar": 0.0,
            "Kv_Ra": 0.02,
            "Kv_Rb": 0.006,
            "Kv_v12": 25,
            "Kv_q": 9,
            "Kv_temp": 23,
            "Kv_q10": 2.3,
            "celsius": 37
        }
        self.channel_states = {
            "Kv_n": 0.0
        }
        self._state_powers = {
            "Kv_n": 1
            }
        self.ion = "k"
        self.current_name = "i_k"

    @property
    def tadj(self):
        q10 = self.channel_params["Kv_q10"]
        temp = self.channel_params["Kv_temp"]
        celsius = self.channel_params["celsius"]
        return q10 ** ((celsius - temp) / 10)

    # def __getitem__(self, item):
    #     return self.channel_params[item]

    def rateconst(self, v, r, th, q):

        rateconst = (r * (v - th)) / (1 - np.exp((-((v - th)) / q)))
        return rateconst

    def compute_kinetic_variables(self, v):
        Ra = self.channel_params["Kv_Ra"]
        Rb = self.channel_params["Kv_Rb"]
        v12 = self.channel_params["Kv_v12"]
        q = self.channel_params["Kv_q"]

        alpn = self.rateconst(v, Ra, v12, q)
        betn = self.rateconst(v, -(Rb), v12, -(q))
        ntau = 1 / (self.tadj * (alpn + betn))
        ninf = alpn / (alpn + betn)
        return [(ninf, ntau),]

    def update_states(self, states, dt, v, params):
        n = states['Kv_n']
        ninf, ntau = self.compute_kinetic_variables(v)
        new_n = exponential_euler(n, dt, ninf, ntau)
        return {
            "Kv_n": new_n
        }

    def compute_current(self, states, v, params):
        n = states['Kv_n']
        gbar = params["Kv_gbar"]
        # E = params["E_k"]
        E = -80
        self.compute_kinetic_variables(v)
        g = self.tadj * gbar * n**1 * 1000
        return g * (v - E)

    def init_state(self, states, v, params, delta_t):
        self.compute_kinetic_variables(v)
        return {
            "Kv_n": self.ninf
        }
