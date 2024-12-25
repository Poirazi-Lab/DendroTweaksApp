Quick Start
==========================================

This tutorial will guide you through the basic steps of creating a :term:`model<Model>`, adding :term:`groups<Section Group>` of :term:`sections<Section>`, distributing :term:`parameters<Distributed parameter>`, defining :term:`spatial discretization<Segmentation>`, adding :term:`mechanisms<Membrane Mechanism>`, setting :term:`global parameters<Global Parameter>`, adding stimuli, running a simulation, and analyzing the results.

Create a model from an SWC file
------------------------------------------

.. code-block:: python

    import dendrotweaks as dd

    model = dd.Model()


.. code-block:: python

    model.from_swc('path/to/swc_file.swc')

More on this in the :doc:`tutorial</tutorials/tutorial_morpho>` on refining neuronal morphology.


Create groups of sections and distribute parameters
---------------------------------------------------

.. code-block:: python

    model.add_group('all')
    model.add_group('soma', lambda sec: sec.domain == 'soma')

.. code-block:: python
    
    model.add_range_param('cm', groups=['all'])
    model.add_range_param('Ra', groups=['all'])
    model.groups['all'].set_distribution('cm', 'uniform', value=1*pF/cm**2)
    model.groups['all'].set_distribution('Ra', 'uniform', value=100*Ohm*cm)

More on this in the :doc:`tutorial</tutorials/tutorial_distributions>` on distributing parameters across the cell.

.. tip::

    Creating groups of sections is easy with the GUI. You can select sections using the interactive plot with a mouse lasso tool, which allows for precise and intuitive selection.

Define spatial discretization
------------------------------------------

.. code-block:: python

    model.set_segmentation(d_lambda=0.1)

.. warning::

    Note that calculating the number of segments involves such parameters as specific membrane capacitance and axial resistance.
    If these parameters are not set, the number of segments will be calculated using default values.

More on this in the :doc:`tutorial</tutorials/tutorial_segmentation>` on setting the spatial discretization of the model.

Add mechanisms and distribute parameters
------------------------------------------

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

Set global parameters
------------------------------------------

.. code-block:: python

    model.set_global_param('e_leak', -70*mV)
    model.set_global_param('e_k', -80*mV)
    model.set_global_param('e_na', 60*mV)
    model.set_global_param('temperature', 37*degC)
    model.set_global_param('v_init', -70*mV)

Add stimuli and run a simulation
------------------------------------------

We will add an current clamp stimulus to the soma and record the somatic membrane potential.

.. code-block:: python

    soma = model.get_sections(lambda sec: sec.domain == 'soma')[0]
    model.add_iclamp(sec=soma, loc=0.5, dur=100*ms, delay=100*ms, amp=150*pA)
    model.add_recording(sec=soma, loc=0.5)
    model.simulator.run(300*ms)

For more complex stimuli, such as synaptic inputs, refer to the :doc:`tutorial</tutorials/tutorial_synapses>`.

Analyze the results
------------------------------------------
.. code-block:: python

    voltage_trace = model.simulator.recordings[0]
    spike_data = dd.validation.count_spikes(voltage_trace)

More on this in the :doc:`tutorial</tutorials/tutorial_validation>` on analyzing simulation results.