Loading Saved Models
==========================================

In this tutorial, we will learn how to load saved models.

Assume we have exported a model.

.. code-block:: bash

    .
    └── data/
        ...
        └── UserModel/  
            ├── membrane/  
            │   ├── config1.json
            │   └── config2.json
            ├── mod/
            │   ├── Kv.mod
            │   └── Nav.mod
            ├── morphology/
            │   ├── cell1.swc
            │   └── cell2.swc
            └── stimuli/ 
                ├── stim1.csv 
                ├── stim1.json
                ├── stim2.csv
                └── stim2.json

.. code-block:: python

    >>> model.list_morphologies()
    ['cell1', 'cell2']


.. code-block:: python

    >>> model.load_morphology('cell1')


.. code-block:: python

    >>> model.list_membrane_configurations()
    ['config1', 'config2']

.. code-block:: python

    >>> model.load_biophysics('config1')


.. code-block:: python

    >>> model.list_stimuli()
    ['stim1', 'stim2']

.. code-block:: python

    >>> model.load_stimuli('stim1')



Note that we can apply the same biophysical model to different morphologies.
After setting up the model with the desired morphology and biophysics
we can upload a different morphology using the :code:`load_morphology` method.

.. code-block:: python

    >>> model.load_morphology('cell2')

Such a parameter transfer of course require the morphologies to come from the same cell type
and share properties such as morphological domains.

We can also dynamically switch to a different stimulatio protocol using the :code:`load_stimuli` method.

.. code-block:: python

    >>> model.load_stimuli('stim2')

