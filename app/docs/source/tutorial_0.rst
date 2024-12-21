Creating a model
==========================================

Reading SWC files
------------------------------------------

.. code-block:: python

    import dendrotweaks as dd

    model = dd.Model()


.. code-block:: python

    model.from_swc('path/to/swc_file.swc')

Create groups of sections

.. code-block:: python

    model.add_group('all')
    model.add_group('soma', lambda sec: sec.domain == 'soma')

.. code-block:: python
    
    model.add_range_param('cm', groups=['all'])
    model.add_range_param('Ra', groups=['all'])
    model.groups['all'].set_distribution('cm', 'uniform', value=1*pF/cm**2)
    model.groups['all'].set_distribution('Ra', 'uniform', value=100*Ohm*cm)

.. code-block:: python

    model.set_segmentation(d_lambda=0.1)

.. code-block:: python

    model.load_mechanisms(archive='Example', recompile=True)

.. code-block:: python

    model.add_range_param('g', mechanism='Leak', groups=['all'])
    model.add_range_param('gbar', mechanism='Nav', groups=['all', 'soma'])
    model.add_range_param('gbar', mechanism='Kv', groups=['all', 'soma'])

.. code-block:: python

    model.groups['all'].set_distribution('g_Leak', 'uniform', value=0.0001*S/cm**2)
    model.groups['all'].set_distribution('gbar_Nav', 'uniform', value=0.03*S/cm**2)
    model.groups['all'].set_distribution('gbar_Kv', 'uniform', value=0.003*S/cm**2)
    model.groups['soma'].set_distribution('gbar_Nav', 'uniform', value=0.05*S/cm**2)
    model.groups['soma'].set_distribution('gbar_Kv', 'uniform', value=0.005*S/cm**2)

.. code-block:: python

    model.set_global_param('e_leak', -70*mV)
    model.set_global_param('e_k', -80*mV)
    model.set_global_param('e_na', 60*mV)
    model.set_global_param('temperature', 37*degC)
    model.set_global_param('v_init', -70*mV)

.. code-block:: python

    soma = model.get_sections(lambda sec: sec.domain == 'soma')[0]
    model.add_iclamp(sec=soma, loc=0.5, dur=100*ms, delay=100*ms, amp=150*pA)
    model.add_recording(sec=soma, loc=0.5)
    model.simulator.run(300*ms)

.. code-block:: python

    voltage_trace = model.simulator.recordings[0]
    spike_data = dd.validation.count_spikes(voltage_trace)