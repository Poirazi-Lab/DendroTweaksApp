Standardizing channel models
==========================================

.. warning::

    Only voltage-gated ion channels can be standardized. The standardization process is not applicable to other mechanisms.

DendroTweaks provides a simple way to standardize voltage-gated ion channel models.
In the previous :ref:`tutorial <tutorial_mod>`, we learned how to load and create ion channels from MOD files.

.. code-block:: python

    >>> model.add_mechanism(
    ...     channel_name='Nav', 
    ...     archive_name='Park_2019',
    ... )

Assuming that the channel models are already loaded into the model, 
we can standardize the voltage-gated sodium ion channel model with just a single line of code.
The standard channel is created to replace the original channel model in the model's :code:`mechanisms` dictionary.
This method also exports the standard channel model to a MOD file which is immediately loaded into the NEURON simulator.

.. code-block:: python

    >>> model.standardize_channel(name='Nav')
    >>> model.mechanisms['sNav'].plot_kinetics()

.. figure:: ../_static/kinetics_standard.png
    :align: center
    :width: 80%
    :alt: Channel kinetics

    *Figure 2: Visualization of channel kinetics (dashed line represents the original channel model)*
    
For some use cases, a standard channel can be created directly using the :code:`MechanismFactory` class.
This method can also be used to convert the original MOD file to a standard channel model as it exports the standard channel to a MOD file
using the specified template.

.. code-block:: python

    >>> std_nav = factory.create_standard_channel(
    ...    channel_name='Nav', 
    ...    archive_name='Park_2019',
    ...    mod_template_name='standard_channel', 
    ...    load=True
    ... )   





How does it work?
-------------------------------------------------------------

Below we provide a brief overview of the standardization process for voltage-gated ion channels.

Current for a given ion channel:

.. math::
    I = \bar{g} \times p(x_1, ..., x_n) \times (V_m - E) 

where:

- :math:`\bar{g}` — the maximum conductance in :math:`S/cm^2`
- :math:`p(x_1, ..., x_n)` — the open probability of the channel
- :math:`V_m` — the membrane potential in :math:`mV`
- :math:`E` — the equilibrium potential in :math:`mV`


Time derivative of a state variable:

.. math::
    \dot{x} = \dfrac{x^{\infty} - x}{\tau_x}

Steady state:

.. math::
    x^{\infty} = \dfrac{1}{1 + \exp \left({-\dfrac{V - V_{half}}{\sigma}}\right)}

Time constant:

.. math::
    \tau_x = \dfrac{1}{\alpha'(V) + \beta'(V)} + \tau_0

where:

.. math::
    \alpha'(V) = K \times \exp \left({\dfrac{\delta \times (V - V_{half})}{\sigma}}\right)

.. math::
    \beta'(V) = K \times \exp \left({\dfrac{-(1 -\delta) \times (V_{half} - V)}{\sigma}}\right)

where:

- :math:`V` — the membrane potential in :math:`mV`
- :math:`V_{half}` — the half-activation potential in :math:`mV`
- :math:`\sigma` — the inverse slope in :math:`mV`
- :math:`\delta` — the skew parameter of the time constant curve (unitless)
- :math:`K` — the maximum rate parameter in :math:`ms^{-1}`
- :math:`\tau_0` — the rate-limiting factor (minimum time constant) in :math:`ms`


