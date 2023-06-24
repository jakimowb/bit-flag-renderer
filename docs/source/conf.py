# -*- coding: utf-8 -*-
"""
***************************************************************************
        begin                : 2019-12-19
        copyright            : (C) 2019 by Benjamin Jakimow
        email                : benjamin.jakimow[at]geo.hu-berlin.de
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************/
"""

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import os, sys, datetime
import mock

if True:
    MOCK_MODULES = ['qgis', 'qgis.core', 'qgis.gui', 'qgis.utils', 'numpy', 'scipy', 'osgeo', 'gdal',
                'qgis.PyQt', 'qgis.PyQt.Qt', 'qgis.PyQt.QtCore', 'qgis.PyQt.QtGui', 'qgis.PyQt.QtWidgets', 'qgis.PyQt.QtXml',
                'processing', 'processing.core', 'processing.core.ProcessingConfig']

    for mod_name in MOCK_MODULES:
        sys.modules[mod_name] = mock.Mock()
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../../'))

try:
    # enable readthedocs to load git-lfs files
    # see https://github.com/rtfd/readthedocs.org/issues/1846
    #     https://github.com/InfinniPlatform/InfinniPlatform.readthedocs.org.en/blob/master/docs/source/conf.py#L18-L31
    # If runs on ReadTheDocs environment
    on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

    if True or on_rtd:
        print('Fetching files with git_lfs')
        DOC_SOURCES_DIR = os.path.dirname(os.path.abspath(__file__))
        PROJECT_ROOT_DIR = os.path.dirname(os.path.dirname(DOC_SOURCES_DIR))
        sys.path.insert(0, DOC_SOURCES_DIR)
        print('PROJECT_ROOT_DIR', PROJECT_ROOT_DIR)

        from git_lfs import fetch
        fetch(PROJECT_ROOT_DIR)
except Exception as ex:
    print(ex)

# -- Project information -----------------------------------------------------

import bitflagrenderer

project = bitflagrenderer.TITLE
copyright = '{}, {}'.format(datetime.datetime.now().year, bitflagrenderer.AUTHOR)
author = bitflagrenderer.AUTHOR

# The full version, including alpha/beta/rc tags
release = bitflagrenderer.__version__
master_doc = 'index'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosectionlabel'
    ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_logo = 'img/bitflagimage.png'
html_favicon = 'img/bitflagimage.png'