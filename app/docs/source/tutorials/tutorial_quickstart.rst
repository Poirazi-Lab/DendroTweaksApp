Quick Start
==========================================

This tutorial will guide you through the basic steps of creating 
a single-cell biophysical neuronal model in DendroTweaks.

Create a model
------------------------------------------

First, we create a model object and specify the path to the folder with the data.

.. code-block:: python

    >>> import dendrotweaks as dd
    >>> model = dd.Model(path_to_data='path/to/data/')

The subfolders of the data folder should follow the structure below wich we can
see using the :code:`model.path_manager.print_directory_tree()` method.

.. code-block:: bash

    .
    └── data/
        ├── Default/    # Default mechanisms
        |  ├── Leak.mod
        |  ├── AMPA.mod
        |  ...
        ├── Templates/  # Jinja2 templates
        |  ├── channel.py
        |  └── standard_channel.mod
        └── UserModel/  # User-defined mechanisms
            ├── morphology/
            │   └── cell.swc
            └── mod/
                ├── Nav.mod
                └── Kv.mod


Load the morphology
------------------------------------------

We proceed by loading the morphology of the cell from an SWC file.
First, we list the available morphologies in the data folder.

.. code-block:: python

    >>> model.list_morphologies()
    ['cell']

We can load the morphology of the cell using the :code:`load_morphology` method.

.. code-block:: python

    >>> model.load_morphology('cell')


We now have access to :code:`swc_tree`, :code:`sec_tree` and :code:`seg_tree`
attributes of the model object.

.. code-block:: python

    >>> model.swc_tree
    >>> model.sec_tree
    >>> model.seg_tree

More on the representation of the neuronal morphology with tree graphs in the :doc:`tutorial</tutorials/tutorial_morpho>`.

.. warning::

    Note that the spatial discretization of the model (i.e. the :code:`seg_tree`) depends on 
    the specific membrane capacitance :code:`cm` and axial resistance :code:`Ra` of the cell.
    By default, these parameters are set to NEURON's default values.
    To learn how to change the spatial discretization of the model refer to the 
    :doc:`tutorial</tutorials/tutorial_segmentation>` on setting the spatial discretization of the model.

Add mechanisms
------------------------------------------

After defining the neuronal morphology, we should proceed with 
specifying its biophysical properties.
Biophysical properties of the model depend on the membrane mechanisms that are inserted into the model.
These mechanisms are defined in MOD files, which are compiled and loaded into NEURON.
We will add the default and user-defined mechanisms to the model and distribute their parameters across the cell.

.. code-block:: python

    >>> model.add_default_mechanisms(recompile=True)
    >>> model.add_mechanisms(recompile=True) # user-defined mechanisms


With this commands we create python objects from MOD files, adding them to :code:`model.mechanisms`.
We also compile MOD files and make them available in NEURON.



We can see the mechanisms available in the model with the :code:`mechanisms` attribute.

.. code-block:: python

    >>> model.mechanisms
    {'Leak': <Mechanism(Leak)>,
     'Nav': <Mechanism(Nav)>,
     'Kv': <Mechanism(Kv)>}

We can see the parameters of the mechanisms in the model with the :code:`params` attribute.

.. code-block:: python

    >>> model.mechanisms['Leak'].params
    {'gbar': 0.0, 'e': -70}

.. warning::

    Note that the parameters stored withing the mechanisms are the default values from the MOD files.
    The actual values of the parameters used for the simulation are stored in the model object!

We can see the parameters of the mechanisms in the model with the :code:`params` attribute.

.. code-block:: python

    >>> model.params
    {'cm': {'all': constant({'value': 1})},
     'Ra': {'all': constant({'value': 35.4})}}

We should interpret the output as follows: the specific membrane capacitance :code:`cm` is set to 1 uF/cm^2,
and the axial resistance :code:`Ra` is set to 35.4 Ohm*cm across the cell. We will discuss how to set these parameters in a bit.

.. warning::

    Note that so far we have only loaded the mechanisms without actually inserting them 
    into the membrane. Therefore, the parameters of the mechanisms are not yet included in the :code:`params` dictionary.
    In the next step we will insert the mechanisms into the membrane.


Insert mechanisms to specific domains
------------------------------------------

In DendroTweaks membrane mechanisms are mapped to the morhological domains.
A domain is a group of sections with similar properties. In a typical pyramidal cell model we have the following domains:
soma, axon, basal dendrites, apical dendrite (further subdivided to trunk, tuft and oblique dendrites).

.. figure:: ../_static/domains2.png
    :align: center
    :width: 80%
    :alt: Domains of a pyramidal cell

    *Figure 1: Domains of a pyramidal cell*

.. code-block:: python

    >>> model.domains
    {'soma': <Domain(soma, 1 sections)>,
     'apic': <Domain(apic, 43 sections)>,
     'axon': <Domain(axon, 1 sections)>,
     'dend': <Domain(dend, 7 sections)>}

To define a new domain, we can use the :code:`define_domain` method.

.. code-block:: python

    >>> sections = model.get_sections(lambda sec: sec.domain == 'apic' and sec.diam < 1)
    >>> model.define_domain('tuft', sections)

.. tip::

    Assigning sections to domains is easy with the GUI.
    You can select sections using the interactive plot with a mouse lasso tool, 
    which allows for precise and intuitive selection.

In the previous step we uploaded the mechanisms, now we want to actually insert them into the specific domains.
In this example we simply insert each of the three mechanism to all domains. However, we could insert some mechanisms only to the soma,
or only to the apical dendrite, etc.

.. code-block:: python

    >>> all_domains = ['soma', 'dend', 'axon', 'apic']
    >>> for domain in all_domains:
    >>>     model.insert_mechanism('Leak', domain)
    >>>     model.insert_mechanism('Nav', domain)
    >>>     model.insert_mechanism('Kv', domain)

We can see the mechanisms inserted in each domain with the :code:`domains_to_mechs` attribute.

.. code-block:: python

    >>> model.domains_to_mechs
    {'soma': ['Leak', 'Nav', 'Kv'],
     'apic': ['Leak', 'Nav', 'Kv'],
     'axon': ['Leak', 'Nav', 'Kv'],
     'dend': ['Leak', 'Nav', 'Kv']}

And we can see the parameters of the mechanisms inserted in the model with the :code:`mechs_to_params` attribute.

.. code-block:: python

    >>> model.mechs_to_params
    {'Independent': ['cm', 'Ra', 'ena', 'ek'],
     'Leak': ['gbar_Leak', 'e_Leak'],
     'Nav': ['gbar_Nav', 'vhalf_m_Nav', ...],
     'Kv': ['gbar_Kv', 'vhalf_n_Kv' ...]}

Some parameters, such as specific membrane capacitance :code:`cm` and axial resistance :code:`Ra`, do not belong to any mechanism.
Such independent parameters are combined under "Independent" pseudo-mechanism for consistency of the interface.
These parameters are avaliable in each domain by default.

If we access the model parameters now, we will see the parameters of the mechanisms inserted in the model.

.. code-block:: python

    >>> model.params
    {'cm': {'all': constant({'value': 1})},
     'Ra': {'all': constant({'value': 35.4})},
     'gbar_Leak': {'all': constant({'value': 0.0}),
     'e_Leak': {'all': constant({'value': -70}),
     'gbar_Nav': {'all': constant({'value': 0.0}),
     'vhalf_m_Nav': {'all': constant({'value': -30}),
     ...
     'ena': {'all': constant({'value': 50}),
     'gbar_Kv': {'all': constant({'value': 0.0}),
     'vhalf_n_Kv': {'all': constant({'value': -35}),
     ...
     'ek': {'all': constant({'value': -77})
     }

As you might have noticed, the default parameter values for 
the mechanisms are uniformly distributed across the entire cell.
This is, however, not always the case in real neurons. Some parameters, such as 
the conductance of ion channels, can vary across the cell. 
DendroTweaks provides a way to distribute parameters across the cell as we discuss in the next section.




Distribute parameters: Where?
------------------------------------------

To distribute parameters across the cell, we need to specify **where** and **how** the parameter will be distributed.

To select the segments where a given distribution will be applied, we will use the segment groups:

.. code-block:: python

    >>> model.groups
    {'all': SegmentGroup("all", domains=['soma', 'apic', 'axon', 'dend']),
     'somatic': SegmentGroup("somatic", domains=['soma']),
     'apical': SegmentGroup("apical", domains=['apic']),
     'axonal': SegmentGroup("axonal", domains=['axon']),
     'dendritic': SegmentGroup("dendritic", domains=['dend'])}

By default a group is created for each domain and the group :code:`all` is created for the entire cell.

We define a segment group by specifying the domains to which the group will be applied, as well as 
a criterion for selecting the segments of the group. This criterion can be the diameter,
the absolute distance (to the root of the tree) or the relative distance within a domain.
Examples of group definitions are shown below:

.. code-block:: python

    >>> model.add_group('thin_apical', domains=['apic'], select_by='diameter', max_val=0.5)
    >>> model.add_group('proximal_dendritic', domains=['dend', 'apic'], select_by='abs_distance', max_val=100)
    >>> model.add_group('hot_spot', domains=['apic'], select_by='rel_distance', min_val=300, max_val=400)

From these definitions you can clearly see the difference between the domains and the groups.
Domains are a logical division of the cell, while groups are a way to select segments based on some criteria.
A group can tear a section apart, so a section's segments can be in multiple groups, as for example the beginning segments of a section 
might satisfy the criteria of one group, while the end segments might not.
Moreover, the domains partition the cell into non-overlapping regions, so that each section belongs to one and only one domain.
Whereas the groups can overlap, so that a segment can belong to multiple groups at the same time.

.. important::

    The order of groups in :code:`model.groups` is important. 
    Groups act like layers, where parameters set in earlier groups 
    can be overwritten by those in later groups. 
    In this example, we first created a group for 'all' sections 
    and then a group specifically for the 'soma'. 
    Thus, for the soma section parameters set for the 'soma' group will overwrite 
    those set for the 'all' group. We can use ::code:`model.move_group_up('soma')` and ::code:`model.move_group_down('soma')` to change the order of groups.



Distribute parameters: How?
------------------------------------------

Now we know where we want to distribute the parameters, we need to specify how we want to distribute them.
We can set the distribution of the parameter for each group. The distribution is a function that
defines how the parameter value changes across the cell. The function
takes the segment distance from the root of the tree and returns the value of the parameter at that segment.

.. figure:: ../_static/distribution.png
    :align: center
    :width: 80%
    :alt: Distribution of parameters across the cell

    *Figure 2: Distribution of parameters across the cell*

In the following example, we set the conductance of the leak channel to one value for all segments,
whereas for the sodium and potassium channels, we set different conductances all segments and then overwrite the values for the soma.

.. code-block:: python

    >>> model.set_param('gbar_Leak', group_name = 'all', distr_type='constant', value=0.0001) # S/cm^2
    >>> model.set_param('gbar_Nav', group_name = 'all', distr_type='constant', value=0.03) # S/cm^2
    >>> model.set_param('gbar_Nav', group_name = 'soma', distr_type='constant', value=0.05) # S/cm^2
    >>> model.set_param('gbar_Kv', group_name = 'all', distr_type='constant', value=0.003) # S/cm^2
    >>> model.set_param('gbar_Kv', group_name = 'soma', distr_type='constant', value=0.005) # S/cm^2


We can also set other parameters, such as reversal potentials, temperature, and initial membrane potential.

.. code-block:: python

    >>> model.set_param('e_Leak', value=-70) # mV
    >>> model.set_param('e_k', value=-80) # mV
    >>> model.set_param('e_na', value=60) # mV
    >>> model.set_param('temperature', value=37) # degC
    >>> model.set_param('v_init', value=-70) # mV

We utilized a more concise notation as these parameters do not vary across the cell.
If we don't provide a group name, the parameter will be set for all segments.
If we don't provide a distribution type, the parameter will be set using a constant distribution.

More on this in the :doc:`tutorial</tutorials/tutorial_distributions>` on distributing parameters across the cell.

Add stimuli and run a simulation
------------------------------------------

We will add a current clamp stimulus to the soma and record the somatic membrane potential.

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