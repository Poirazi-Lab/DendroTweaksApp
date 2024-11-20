
class Simulator:
    def __init__(self):
        pass


class NEURONSimulator(Simulator):
    """
    A class to represent a NEURON simulator.
    """

    def __init__(self, celsius=37, v_init=-70, dt=0.025, cvode=False):
        super().__init__()
        from neuron import h
        from neuron.units import ms, mV
        self.h = h
        self.h.load_file('stdrun.hoc')
        # self.h.load_file('import3d.hoc')
        # self.h.load_file('nrngui.hoc')
        # self.h.load_file('import3d')

        self.celsius = celsius
        self.v_init = v_init * mV

        self.dt = dt
        self._cvode = cvode

        self.recordings = {}
        # self.t = []

    def add_recording(self, seg, var='v'):
        if self.recordings.get(seg):
            self.remove_recording(seg)
        self.recordings[seg] = self.h.Vector().record(getattr(seg._ref, f'_ref_{var}'))

    def remove_recording(self, seg, var='v'):
        if self.recordings.get(seg):
            self.recordings[seg] = None
            self.recordings.pop(seg)

    def remove_all_recordings(self):
        for seg in list(self.recordings.keys()):
            self.remove_recording(seg)
        # self.recordings = {}

    def _init_simulation(self):
        self.h.CVode().active(self._cvode)
        self.h.celsius = self.celsius
        self.h.dt = self.dt
        self.h.stdinit()
        self.h.init()
        self.h.finitialize(self.v_init)
        if self.h.cvode.active():
            self.h.cvode.re_init()
        else:
            self.h.fcurrent()
        self.h.frecord_init()

    def run(self, duration=300):

        from neuron.units import ms, mV

        vs = [v for v in self.recordings.values()]
        Is = []

        # for v in self.recordings.values():
        #     # v = h.Vector().record(seg._ref_v)
        #     vs.append(v)

        t = self.h.Vector().record(self.h._ref_t)
        self.t = t

        # if self.ch is None:
        #     pass
        # else:
        #     for seg in self.recordings.keys():
        #         if getattr(seg, f'_ref_i_{self.ch.suffix}', None) is None:
        #             logger.warning(
        #                 f'No current recorded for {self.ch.suffix} at {seg}. Make i a RANGE variable in mod file.')
        #             continue
        #         I = h.Vector().record(getattr(seg, f'_ref_i_{self.ch.suffix}'))
        #         Is.append(I)

        self._init_simulation()

        self.h.continuerun(duration * ms)

        return [t.to_python() for _ in vs], [v.to_python() for v in vs], [i.to_python() for i in Is]

    def to_dict(self):
        return {
            'temperature': self.celsius,
            'v_init': self.v_init,
            'dt': self.dt,
        }


class JaxleySimulator(Simulator):
    """
    A class to represent a Jaxley simulator.
    """

    def __init__(self):
        super().__init__()
        ...

    
