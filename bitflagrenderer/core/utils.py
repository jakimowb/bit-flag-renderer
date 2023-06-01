import io
import os
import re
import sys

import numpy as np

from bitflagrenderer import NEXT_COLOR_HUE_DELTA_CON, NEXT_COLOR_HUE_DELTA_CAT
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtXml import QDomDocument

from qgis.PyQt import uic
from qgis.core import Qgis


def contrastColor(c: QColor) -> QColor:
    """
    Returns a QColor with good contrast to the input color c
    :param c: QColor
    :return: QColor
    """
    assert isinstance(c, QColor)
    if c.lightness() < 0.5:
        return QColor('white')
    else:
        return QColor('black')


def nextColor(color, mode='cat') -> QColor:
    """
    Returns another color.
    :param color: QColor
    :param mode: str, 'cat' for categorical colors (much difference from 'color')
                      'con' for continuous colors (similar to 'color')
    :return: QColor
    """
    assert mode in ['cat', 'con']
    assert isinstance(color, QColor)
    hue, sat, value, alpha = color.getHsl()
    if mode == 'cat':
        hue += NEXT_COLOR_HUE_DELTA_CAT
    elif mode == 'con':
        hue += NEXT_COLOR_HUE_DELTA_CON
    if sat == 0:
        sat = 255
        value = 128
        alpha = 255
        s = ""
    while hue > 360:
        hue -= 360

    return QColor.fromHsl(hue, sat, value, alpha)


def loadUi(uifile, baseinstance=None, package='', resource_suffix='_rc', remove_resource_references=True,
           loadUiType=False):
    """
    :param uifile:
    :type uifile:
    :param baseinstance:
    :type baseinstance:
    :param package:
    :type package:
    :param resource_suffix:
    :type resource_suffix:
    :param remove_resource_references:
    :type remove_resource_references:
    :return:
    :rtype:
    """

    assert os.path.isfile(uifile), '*.ui file does not exist: {}'.format(uifile)

    with open(uifile, 'r', encoding='utf-8') as f:
        txt = f.read()

    dirUi = os.path.dirname(uifile)

    locations = []

    for m in re.findall(r'(<include location="(.*\.qrc)"/>)', txt):
        locations.append(m)

    missing = []
    for t in locations:
        line, path = t
        if not os.path.isabs(path):
            p = os.path.join(dirUi, path)
        else:
            p = path

        if not os.path.isfile(p):
            missing.append(t)

    match = re.search(r'resource="[^:].*/QGIS[^/"]*/images/images.qrc"', txt)
    if match:
        txt = txt.replace(match.group(), 'resource=":/images/images.qrc"')

    if len(missing) > 0:

        missingQrc = []
        missingQgs = []

        for t in missing:
            line, path = t
            if re.search(r'.*(?i:qgis)/images/images\.qrc.*', line):
                missingQgs.append(m)
            else:
                missingQrc.append(m)

        if len(missingQrc) > 0:
            print('{}\nrefers to {} none-existing resource (*.qrc) file(s):'.format(uifile, len(missingQrc)))
            for i, t in enumerate(missingQrc):
                line, path = t
                print('{}: "{}"'.format(i + 1, path), file=sys.stderr)

    doc = QDomDocument()
    doc.setContent(txt)

    elem = doc.elementsByTagName('customwidget')
    for child in [elem.item(i) for i in range(elem.count())]:
        child = child.toElement()

        cClass = child.firstChildElement('class').firstChild()
        cHeader = child.firstChildElement('header').firstChild()
        cExtends = child.firstChildElement('extends').firstChild()

        sClass = str(cClass.nodeValue())
        sExtends = str(cHeader.nodeValue())

    if remove_resource_references:
        # remove resource file locations to avoid import errors.
        elems = doc.elementsByTagName('include')
        for i in range(elems.count()):
            node = elems.item(i).toElement()
            attribute = node.attribute('location')
            if len(attribute) > 0 and attribute.endswith('.qrc'):
                node.parentNode().removeChild(node)

        # remove iconset resource names, e.g.<iconset resource="../qpsbitflagrenderer.qrc">
        elems = doc.elementsByTagName('iconset')
        for i in range(elems.count()):
            node = elems.item(i).toElement()
            attribute = node.attribute('resource')
            if len(attribute) > 0:
                node.removeAttribute('resource')

    buffer = io.StringIO()  # buffer to store modified XML
    buffer.write(doc.toString())
    buffer.flush()
    buffer.seek(0)

    if not loadUiType:
        return uic.loadUi(buffer, baseinstance=baseinstance, package=package, resource_suffix=resource_suffix)
    else:
        return uic.loadUiType(buffer, resource_suffix=resource_suffix)


QGIS2NUMPY_DATA_TYPES = {Qgis.Byte: np.byte,
                         Qgis.UInt16: np.uint16,
                         Qgis.Int16: np.int16,
                         Qgis.UInt32: np.uint32,
                         Qgis.Int32: np.int32,
                         Qgis.Float32: np.float32,
                         Qgis.Float64: np.float64,
                         #  Qgis.CFloat32: np.complex,
                         #  Qgis.CFloat64: np.complex64,
                         Qgis.ARGB32: np.uint32,
                         Qgis.ARGB32_Premultiplied: np.uint32}
