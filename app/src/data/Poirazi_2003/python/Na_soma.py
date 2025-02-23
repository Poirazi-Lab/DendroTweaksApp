# This Python channel class was automatically generated from a MOD file
# using DendroTweaks toolbox, dendrotweaks.dendrites.gr

import sys

from dendrotweaks.membrane.mechanisms import IonChannel
import numpy as np

class Na_soma(IonChannel):
    """
    NaV somatic Na+ channel from Poirazi et al. 2003 hh mechanism
    """

    def __init__(self, name="Na_soma"):
        super().__init__(name=name)
        self.params = {
            "gbar": 0,
            "a0r": 0.0003,
            "b0r": 0.0003,
            "zetar": 12,
            "gmr": 0.2,
            "ar2": 1.0,
            "taumin": 3,
            "vvs": 2,
            "vhalfr": -60
            }
        self.range_params = {
            "gbar": 0,
            "ar2": 1.0
            }
        self.states = {
            "m": 0.0,
            "h": 0.0,
            "s": 0.0
            }
        self._state_powers = {
            "m": {'power': 2},
            "h": {'power': 1},
            "s": {'power': 1}
            }
        self.ion = "na"
        self.current_name = "i_na"
        self.independent_var_name = "v"

    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, item, value):
        self.params[item] = value

    
    def compute_kinetic_variables(self, v):
        a0r = self.params["a0r"]
        b0r = self.params["b0r"]
        taumin = self.params["taumin"]
        vhalfr = self.params["vhalfr"]
        
        mInf = 1 / (1 + np.exp(((v + 44) / -3)))
        mTau = 0.05
        hInf = 1 / (1 + np.exp(((v + 49) / 3.5)))
        hTau = 1
        sInf = self.alpv(v, vhalfr)
        tmp = self.betr(v) / (a0r + (b0r * self.alpr(v)))
        conditions = [tmp < taumin, ~(tmp < taumin)]
        choices = [taumin, tmp]
        tmp = np.select(conditions, choices)
        sTau = tmp
        return mInf, mTau, hInf, hTau, sInf, sTau
    
    
    def alpv(self, v, vh):
        ar2 = self.params["ar2"]
        vvs = self.params["vvs"]
        
        alpv = (1 + (ar2 * np.exp(((v - vh) / vvs)))) / (1 + np.exp(((v - vh) / vvs)))
        return alpv
    
    def alpr(self, v):
        zetar = self.params["zetar"]
        vhalfr = self.params["vhalfr"]
        
        alpr = np.exp(((((0.001 * zetar) * (v - vhalfr)) * 96480.0) / (8.315 * (273.16 + celsius))))
        return alpr
    
    def betr(self, v):
        zetar = self.params["zetar"]
        gmr = self.params["gmr"]
        vhalfr = self.params["vhalfr"]
        
        betr = np.exp((((((0.001 * zetar) * gmr) * (v - vhalfr)) * 96480.0) / (8.315 * (273.16 + celsius))))
        return betr