Quick Start
==========================================

This tutorial will guide you through the basic steps of creating a model, 
adding groups of sections, distributing parameters, defining spatial discretization, 
adding mechanisms, setting global parameters, adding stimuli, running a simulation, 
and analyzing the results.

Create a model
------------------------------------------

First, we create a model object and specify the path to the data directory.

.. code-block:: python

    >>> import dendrotweaks as dd
    >>> model = dd.Model('path/to/data/')

An example of the data directory structure is shown below. 

.. code-block:: bash

    .
    └── data/
        ├── mod/
        │   ├── Default/
        │   │   └── Leak.mod
        |   ├── Synapses/
        │   │   ├── AMPA.mod
        │   │   └── NMDA.mod
        │   └── User/
        │       ├── Kv.mod
        │       └── Nav.mod
        ├── python/
        │   └── User/
        │       ├── Kv.py
        │       └── Nav.py
        ├── swc/
        │   └── Cell.swc
        └── templates/
            ├── default.py
            └── standard.mod

Load the morphology
------------------------------------------

We proceed by loading the morphology of the cell from an SWC file.

.. code-block:: python

    >>> model.from_swc('filename.swc')

More on this in the :doc:`tutorial</tutorials/tutorial_morpho>` on refining neuronal morphology.

We now have access to :code:`swc_tree` and :code:`sec_tree` attributes of the model object.

.. code-block:: python

    >>> model.swc_tree
    >>> model.sec_tree

Define spatial discretization
------------------------------------------

Next, we need to build :code:`seg_tree` and define the spatial discretization of the model.
For this, we need to set the specific membrane capacitance :code:`cm` and axial resistance :code:`Ra` of the cell.

.. code-block:: python

    >>> model.set_global_param('cm', 1) # uF/cm^2
    >>> model.set_global_param('Ra', 100) # Ohm*cm

We can now set the spatial discretization of the model.

.. code-block:: python

    >>> model.set_segmentation(d_lambda=0.1)

.. warning::

    Note that calculating the number of segments involves such parameters 
    as specific membrane capacitance :code:`cm` and axial resistance :code:`Ra`.
    If these parameters are not set, the number of segments will be calculated using default NEURON values.
    

More on this in the :doc:`tutorial</tutorials/tutorial_segmentation>` on setting the spatial discretization of the model.

Add mechanisms
------------------------------------------

We will add the default and user-defined mechanisms to the model and distribute their parameters across the cell.

.. code-block:: python

    >>> model.add_mechanisms(dir_name='Default', recompile=True)
    >>> model.add_mechanisms(dir_name='User', recompile=True)



With this commands we create python objects from MOD files, adding them to :code:`model.mechanisms`.
We also compile MOD files and make them avaliable in NEURON.


Create section groups and insert mechanisms
------------------------------------------

.. code-block:: python

    >>> model.add_group('all')
    >>> model.add_group('soma', lambda sec: sec.domain == 'soma')
    >>> model.groups

.. tip::

    Creating groups of sections is easy with the GUI. You can select sections using the interactive plot with a mouse lasso tool, which allows for precise and intuitive selection.


Next, we specify the section groups to which the mechanisms will be added.

.. code-block:: python

    >>> model.insert_mechanism('Leak', group_name='all')
    >>> model.insert_mechanism('Nav', group_name='all')
    >>> model.insert_mechanism('Nav', group_name='soma')
    >>> model.insert_mechanism('Kv', group_name='all')
    >>> model.insert_mechanism('Kv', group_name='soma')

Some parameters, such as specific membrane capacitance :code:`cm` and axial resistance :code:`Ra`, do not belong to any mechanism.
Such independent parameters are combined under "Independent" pseudo-mechanism for consistency of the interface.
The "Independent" pseudo-mechanism is added to each group by default.

Distribute parameters
------------------------------------------

By default each parameter is a global parameter, meaning that it has the same value across the cell.

As we did it before for :code:`cm` and :code:`Ra`, we can update the value of the parameter for the whole cell.

.. code-block:: python

    >>> model.set_global_param('g_Leak', 0.0001) # S/cm^2

However, in some cases (e.g. for ion channel conductances) we want to distribute the parameter across the cell
in a non-homogeneous way. We can do this by setting the distribution of the parameter for each group.

We first make the parameter distributed.

.. code-block:: python

    >>> model.make_distributed('gbar_Nav')
    >>> model.make_distributed('gbar_Kv')

Now we can set the distribution of the parameter for each group.

.. code-block:: python

    >>> model.set_distributed_param('gbar_Nav', group_name = 'all', distr_type='uniform', value=0.03) # S/cm^2
    >>> model.set_distributed_param('gbar_Nav', group_name = 'soma', distr_type='uniform', value=0.05) # S/cm^2
    >>> model.set_distributed_param('gbar_Kv', group_name = 'all', distr_type='uniform', value=0.003) # S/cm^2
    >>> model.set_distributed_param('gbar_Kv', group_name = 'soma', distr_type='uniform', value=0.005) # S/cm^2

.. important::

    The order of groups in :code:`model.groups` is important. 
    Groups act like layers, where parameters set in earlier groups 
    can be overwritten by those in later groups. 
    In this example, we first created a group for 'all' sections 
    and then a group specifically for the 'soma'. 
    Thus, for the soma section parameters set for the 'soma' group will overwrite 
    those set for the 'all' group.

More on this in the :doc:`tutorial</tutorials/tutorial_distributions>` on distributing parameters across the cell.


Set other global parameters
------------------------------------------

.. code-block:: python

    >>> model.set_global_param('e_Leak', -70) # mV
    >>> model.set_global_param('e_k', -80) # mV
    >>> model.set_global_param('e_na', 60) # mV
    >>> model.set_global_param('temperature', 37) # degC
    >>> model.set_global_param('v_init', -70) # mV

Add stimuli and run a simulation
------------------------------------------

We will add an current clamp stimulus to the soma and record the somatic membrane potential.

First, we select the soma section of the model.

.. code-block:: python

    >>> soma = model.get_sections(lambda sec: sec.domain == 'soma')[0]

Next, we add a recording point at the center of the soma.

.. code-block:: python

    >>> model.add_recording(sec=soma, loc=0.5)

Then, we add a current clamp stimulus to the center of the soma.

.. code-block:: python

    >>> model.add_iclamp(sec=soma, loc=0.5, dur=100*ms, delay=100*ms, amp=150*pA)

Finally, we run the simulation for 300 milliseconds.

.. code-block:: python

    >>> model.simulator.run(300) # ms

For more complex stimuli, such as synaptic inputs, refer to the :doc:`tutorial</tutorials/tutorial_synapses>`.

Analyze the results
------------------------------------------
.. code-block:: python

    >>> voltage_trace = model.simulator.recordings[0]
    >>> pike_data = dd.validation.count_spikes(voltage_trace)

More on this in the :doc:`tutorial</tutorials/tutorial_validation>` on analyzing simulation results.