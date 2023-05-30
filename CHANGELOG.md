# Changelog

## Version 0.5

- fixed numpy data types
- refactoring

## Version 0.4

- changed group checkbox selection behaviour: selecting the entire Bit Flag Group will select all
  BitFlagStates except the 1st = empty flag (closes #6)
- added context menu, e.g. to edit bit flag states and colors
- added Landsat Level-2 pixel_qa scheme (closes #10)
- fixed double click edit options (closes #4)
- fixed initial visibility for bit flag states loaded from XML (closes #8)


## Version 0.3

- loading a bit flag scheme updates the raster layer renderer
- reversed bit rendering order. least significant bit is rendered last, e.g. a "top layer"
- fixed FORCE bit flag scheme and uses FORCE overview image (OVV) colors by default

## Version 0.2

 - tree view recalls expansion state of flag parameter nodes
 - fixed saving of Flag Schemes
 - cleaned code, removed a PPT from docs (issue #1)

## Version 0.1

 - first version
 - predefined flag schemes for Landsat 4-8 QA bands and FORCE QAI
 - flag schemes can be saved and restored to/from XML files
 - example data set with Landsat 8 TOA + Quality Assessment image