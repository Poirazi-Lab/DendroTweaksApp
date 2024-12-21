Working with neuronal morphologies
==========================================

Reading SWC files
------------------------------------------

Example of an swc file as a table:

.. table:: 
   :widths: 10 10 10 10 10 10 10

   +----+------+-------+-------+-------+-------+-------+
   | id | type |   x   |   y   |   z   |radius |parent |
   +====+======+=======+=======+=======+=======+=======+
   |  1 |    1 | 0.0   | 0.0   | 0.0   | 1.0   |  -1   |
   +----+------+-------+-------+-------+-------+-------+
   |  2 |    3 | 0.0   | 1.0   | 0.0   | 0.5   |   1   |
   +----+------+-------+-------+-------+-------+-------+
   |  3 |    3 | 1.0   | 1.0   | 0.0   | 0.5   |   2   |
   +----+------+-------+-------+-------+-------+-------+


Creating an SWC tree from an SWC file
------------------------------------------

.. code-block:: python

    from dendrotweaks.morphology import SWCTree
    swc_tree = SWCTree.from_swc('path/to/swc_file.swc')

1. Sort

.. code-block:: python

    swc_tree.sort()

2. Split to sections

.. code-block:: python

    swc_tree.split_to_sections()


3. Extend the sections

.. code-block:: python

    swc_tree.extend_sections()


4. Shift and rotate

.. code-block:: python

    swc_tree.shift_and_rotate()
