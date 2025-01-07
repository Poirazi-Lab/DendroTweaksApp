Distributing Parameters
==========================================

In this tutorial, we will learn how to distribute parameters across the cell using the :code:`dendrotweaks` package.

The simplest case is to assign a single value to a parameter for all sections of the cell. For example, to set the capacitance :code:`cm` to 1 pF/cm^2 and the axial resistance :code:`Ra` to 100 Ohm*cm, we can use the following code:

.. code-block:: python

    >>> model.set_global_parameter('cm', 1.0)
    >>> model.set_global_parameter('Ra', 100.0)

.. code-block:: python

    >>> model.global_params
    {'cm': 1, 'Ra': 100, 'ena': 50, 'ek': -77}

However, in many cases, we want to set different values for different groups of sections. Ion channels, for example, are often distributed non-uniformly across the cell. To achieve this, we can create groups of sections and assign distribution functions to parameters.

Selecting sections
------------------------------------------

We can access sections of the cell using :code:`model.get_sections()`. This method takes a lambda function as an argument, 
which is used to filter sections based on their properties. For example, to get all sections of the soma, we can use the following code:

.. code-block:: python

   >>> model.get_sections(lambda sec: sec.domain == 'soma')

Calling this method without any arguments will return all sections of the cell.

Sections can be selected by the following properties:

* `domain` - The type of the section as defined in the SWC file (e.g., soma, axon, dendrite)
* `diam` - The diameter of the section in micrometers (e.g., diam > 1)
* `distance` - The distance of the section from the soma in micrometers (e.g., distance > 100)

To select sections based on multiple properties, use the `&` operator:

.. code-block:: python

    >>> apic_thin = model.get_sections(lambda sec: sec.domain == 'apic' & sec.diam < 1)

Creating groups of sections
------------------------------------------

To create groups of sections, we can use the :code:`add_group` method. We can either provide the sections directly or use a lambda function to filter them.
For example, to create a group of apical sections, we can use the following code:

.. code-block:: python

    >>> sections = model.get_sections(lambda sec: sec.domain == 'apic')
    >>> model.add_group('apic', sections=sections)
    >>> # alternatively: 
    >>> model.add_group('apic', lambda sec: sec.domain == 'apic')
    

.. tip::
    Many methods in the :code:`Model` class have their hidden counterparts.
    For example, :code:`add_group` has a hidden method :code:`_add_group` based on dependency injection rather than construction, which can be useful in some cases.
    
    .. code-block:: python

        >>> group = dd.Group('apic', lambda sec: sec.domain == 'apic')
        >>> model._add_group(group)

Groups as layers
------------------------------------------

Groups can be thought of as layers rather than partitions of the cell. This representation implies that groups are not mutually exclusive; a section can belong to multiple groups. For example, you can have a group for all sections and another group for apical sections, where the apical sections are a subset of all sections.

.. important::

    Note that if a section belongs to multiple groups the parameters will be assigned from the top-most of the groups.

This layer-based approach has several advantages. The most important one is that if a group of sections is removed, the sections will revert to the previous layer they belonged to. By default, the entire cell is considered a single group called 'all', which serves as the base layer.

We can move groups up and down in the layer stack using the :code:`move_group_up` and :code:`move_group_down` methods. For example, to move the 'apic' group up and down, we can use the following code:

.. code-block:: python

    >>> model.move_group_down('apic')
    >>> model._groups
    [Group("apic", 52), Group("soma", 1)]


Distributing Parameters
------------------------------------------

The main purpose of groups of sections is to distribute parameters across the cell. 
Each range parameter can be assigned a distribution function that 
will be used to generate values for each segment for each section in the group based on the segment's distance from the soma.

.. math::

    f: \text{Distances} \rightarrow \text{Values}

The functions are defined in the :code:`dendrotweaks.distributions` module as parametrized callable objects.

We can create a distribution function using the :code:`create_distribution` method. For example, to create a uniform distribution with a value of 1 pF/cm^2, we can use the following code:

.. code-block:: python

    >>> uniform = dd.Distribution('uniform', value=1)


The following distribution functions (and their parameters) are available:

.. code-block:: python

    >>> uniform = dd.Distribution('uniform', value=1)
    >>> linear = dd.Distribution('linear', slope=1, intercept=0)
    >>> exponential = dd.Distribution('exponential', base=2, value=1)
    >>> normal = dd.Distribution('normal', mean=100, std=10)

Assigning functions to parameters
------------------------------------------

To assign a distribution function to a parameter, we can use the :code:`set_distribution` method. For example, to assign the uniform distribution to the capacitance parameter :code:`cm` for all sections, we can use the following code:

.. code-block:: python

    >>> model.make_distributed('cm')

.. code-block:: python

    >>> model.set_distributed_param('cm', group_name='all', distr_type='uniform', value=1)
    >>> model.set_distributed_param('cm', group_name='soma', distr_type='uniform', value=2)

.. code-block:: python

    >>> model.distributed_params
    {'cm': {'all': Distribution("uniform", 1), 'soma': Distribution("uniform", 2)}

Combining Distributions
------------------------------------------

Distributions can be combined. For example a step-like distribution can be created by combining two uniform distributions:

.. code-block:: python

    >>> model.add_group('apic', lambda sec: sec.domain == 'apic')
    >>> model.set_distributed_param('gbar_Cav', group_name='apic', distr_type='uniform', value=0.0001)
    >>> model.add_group('apic_hot_spot', lambda sec: sec.domain == 'apic' & 100 < sec.distance < 200)
    >>> model.set_distributed_param('gbar_Cav', group_name='apic_hot_spot', distr_type='uniform', value=0.001)
    