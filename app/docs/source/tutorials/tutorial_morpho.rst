Neuronal morphologies
==========================================


What are SWC files?
-------------------

SWC files are a standard format for representing neuronal morphologies. They consist of a series of lines, each describing a point in the neuron with specific attributes. Below is an example of an SWC file represented as a table:

.. table:: Example SWC File
    :widths: 10 10 10 10 10 10 10
    :align: center

    +-------+------+-------+-------+-------+-------+--------+
    | Index | Type |   X   |   Y   |   Z   |   R   | Parent |
    +=======+======+=======+=======+=======+=======+========+
    |   1   |   1  |  0.0  |  0.0  |  0.0  |  1.0  |   -1   |
    +-------+------+-------+-------+-------+-------+--------+
    |   2   |   3  |  0.0  |  1.0  |  0.0  |  0.5  |    1   |
    +-------+------+-------+-------+-------+-------+--------+
    |   3   |   3  |  1.0  |  1.0  |  0.0  |  0.5  |    2   |
    +-------+------+-------+-------+-------+-------+--------+

Each line in an SWC file contains the following fields:

- **Index**: Sample identifier. A sequential positive integer.
- **Type**: Type identifier. A positive integer:
    - 0: Structure type unknown or unspecified
    - 1: Soma of a neuron
    - 2: Axon of a neuron
    - 3: Basal dendrite of a neuron
    - 4: Apical dendrite of a neuron
    - 5: Custom type of cell component
    - 6: An unspecified part of a neuron
    - 7: Glial processes
    - >7: Custom type of cell component
- **X**: X-position in micrometers.
- **Y**: Y-position in micrometers.
- **Z**: Z-position in micrometers.
- **R**: Radius in micrometers (half the node thickness).
- **Parent**: Parent sample identifier.

For more details, refer to the `SWC specification <https://swc-specification.readthedocs.io/en/latest/swc.html>`_.

Representing morphologies in DendroTweaks
---------------------------------------------

In DendroTweaks, morphologies are represented as tree graphs. Each tree consists of nodes that represent the points in the SWC file. The nodes are connected by edges that represent the parent-child relationships between the points. The tree structure allows for easy traversal and manipulation of the morphology.


.. image:: ../_static/trees.png
    :width: 80%
    :align: center

The :class:`SWCTree` class in DendroTweaks provides methods for creating and working with SWC trees. Below are some examples of how to work with SWC trees in DendroTweaks.

Shortcut for creating morphology
------------------------------------------------

DendroTweaks provides a shortcut for creating a morphology from an SWC file that we have already seen in the first :doc:`tutorial</tutorials/tutorial_quickstart>`. You can use the :code:`from_swc` method to create a morphology from an SWC file:

.. code-block:: python

    >>> model.from_swc('path/to/swc_file.swc')

This method automatically sorts the points, splits them into sections, extends the sections, and shifts and rotates the morphology to a standard orientation.
The trees are then stored in the :code:`model` object for further processing.

.. code-block:: python
    
        >>> model.swc_tree, model.sec_tree
        <dendrotweaks.morphology.SWCTree at 0x7f8b3b3b3b50>

For more details on working with SWC trees in DendroTweaks, refer to the :doc:`tutorial</tutorials/tutorial_swc>` on refining neuronal morphology.

Creating the segmentation tree requires us to set the passive properties of the sections. 
Therefore in the next tutorial we will discuss how we can define properties in our model.


