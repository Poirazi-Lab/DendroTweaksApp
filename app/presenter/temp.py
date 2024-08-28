# Note that TempMixin is a temporary class that will be removed in the future
# It is used to update some model parameters for which the GUI is not yet implemented

import numpy as np
from logger import logger


class TempMixin():

    def __init__(self):
        logger.debug('TempMixin init (to be removed)')
        super().__init__()

    def Ca_dyn_temp(self):

        self.view.widgets.selectors['mod_files_cadyn'].value = 'Hay_cadyn'

        for sec in self.model.cell.soma:
            for seg in sec:
                seg.decay_cadynhay = 460
                seg.gamma_cadynhay = 0.000501

        for sec in self.model.cell.apic:
            for seg in sec:
                seg.decay_cadynhay = 122
                seg.gamma_cadynhay = 0.000509

    def Ra_sigmoidal_temp(self):

        for sec in self.model.cell.soma:
            for seg in sec:
                seg.K_h = 8.8
                seg.vhalf_h = -82

        # this part is for Ih experiment (block Ih in the model)
        # for sec in self.model.cell:
        #     for seg in sec:
        #         seg.gbar_h *= 0.2

        for sec in self.model.cell.soma:
            sec.Ra = 50

        for sec in self.model.cell.dend:
            sec.Ra = 50

        for sec in self.model.cell.axon:
            sec.Ra = 50

        for sec in self.model.cell.apic:
            sec.Ra = 50

        def sigmoidal(distance, vertical_shift, scale_factor, growth_rate, horizontal_shift):
            return vertical_shift + scale_factor / (1 + np.exp(-growth_rate*(distance - horizontal_shift)))

        apic = self.model.cell.apic
        trunk_sections = [apic[0],  
                        apic[4],  
                        apic[6],  
                        apic[14], 
                        apic[15], 
                        apic[16], 
                        apic[22], 
                        apic[23], 
                        apic[25], 
                        apic[26], 
                        apic[27], 
                        apic[41], 
                        apic[42], 
                        apic[46], 
                        apic[48], 
                        apic[56], 
                        apic[58], 
                        apic[60], 
                        apic[62], 
                        apic[64], 
                        apic[65], 
                        apic[69], 
                        apic[71], 
                        apic[81], 
                        apic[83], 
                        apic[95], 
                        apic[103], 
                        apic[104]]

        for sec in trunk_sections:
            sec.Ra = sigmoidal(self.model.cell.distance_from_soma(sec(0.5)), 
                               vertical_shift = 34.7387906793,
                               scale_factor = 14.6740500337,
                               growth_rate = -0.0117912091,
                               horizontal_shift = 533.9617117381)

        self.update_graph_param('Ra')


        max_ar2 = 0.95  # Somatic value of ar2
        min_ar2 = 0.30  # Minimum value of ar2
        decay_end = 650#300.0  # Distance beyond which all values are min_ar2
        decay_start = 300 #50.0  # Distance at which ar2 starts to decrease
        m_ar2 = (max_ar2 - min_ar2) / (decay_start - decay_end)

        def ar2(xdist):
            if xdist < decay_start:
                return max_ar2
            elif xdist > decay_end:
                return min_ar2
            else:
                return max_ar2 + m_ar2 * xdist

        for sec in trunk_sections:
            for seg in sec:
                seg.ar2_nav_dend = ar2(xdist=self.model.cell.distance_from_soma(seg))


    