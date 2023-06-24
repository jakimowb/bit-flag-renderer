.. Flag Raster Renderer documentation master file

Bit Flag Renderer
-----------------

About
-----

The Bit Flag Renderer is a QGIS Plugin to visualize bit flags in raster quality images.

The Bit Flag Renderer is developed at Humboldt-Universität zu Berlin,
`Earth Observation Lab <https://hu-berlin.de/eo-lab>`_ as part of the
`Land Use Monitoring System (LUMOS) <https://eo.belspo.be/en/stereo-in-action/projects/remote-sensing-image-processing-algorithms-land-use-and-land-cover>`_
project, funded by the Belgian Science Policy Office as part of the Stereo-III research program (grant no. SR/01/349).


Features
--------

* visualizes bit flags consisting of 1 to 3 bits (from 2 (on/off) to 8 different states)
* layer legend shows flag state colors
* predefined flag schemes, e.g. for [Landsat Quality Assessment (QA) bands](https://www.usgs.gov/landsat-missions/landsat-surface-reflectance-quality-assessment)
* allows to specify, save and reload flag schemes
* Documentation [https://bit-flag-renderer.readthedocs.io/en/latest](https://bit-flag-renderer.readthedocs.io/en/latest)
* Repository [https://bitbucket.org/jakimowb/bit-flag-renderer](https://bitbucket.org/jakimowb/bit-flag-renderer)


.. |workflow| image:: img/usage.png


How to Use
----------

.. figure:: img//usage.png
   :width: 100%

   Clouds and shadows according to the Landsat quality assessment (QA) flag layer, visualized with the Bit Flag Renderer panel

To visualize bit flags of a byte/integer raster layer, select this layer in the QGIS raster layer tree and
open the QGIS Layer Styling Panel. Then:

1. Select the Bit Flag Renderer sub panel

2. Add the number of Bit Flag parameter that you like to show or open load a pre-defined scheme of bit flags

3. Specify for each parameter (double click) the first bit position and the total number of bit the parameter is using. The total number of bits
   controls the number of possible states a parameter can have per pixel, e.g.

    - '0' for the first bit = 2 flag states
    - '1' for the second bit = 2 flag states
    - '1-2' for bit 1 and 2 = 2^2 = 4 flag states
    - '1-3' for bit 1, 2 and 3 = 2^3 = 8 flag states

Now control the visibility of flag states in the map and layer legend:

* Change flag state visibility by checking/unchecking them in the tree view
* Define names of parameters and flag state (double click)
* Define flag state colors (double click)


.. table::

   ==================== ================================================================================================
   Online documentation https://readthedocs.org/projects/bit-flag-renderer/
   Source Code          https://bitbucket.org/jakimowb/bit-flag-renderer
   Issue tracker        https://bitbucket.org/jakimowb/bit-flag-renderer/issues
   ==================== ================================================================================================

License and Use
---------------

This program is free software; you can redistribute it and/or modify it under the terms of the `GNU General Public License Version 3 (GNU GPL-3) <https://www.gnu.org/licenses/gpl-3.0.en.html>`_ , as published by the Free Software Foundation. See also :ref:`License`.

.. toctree::
   :maxdepth: 4