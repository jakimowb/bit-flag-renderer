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

from bitflagrenderer.bitflagrenderer import BitFlagScheme, BitFlagParameter
from qgis.PyQt.QtGui import QColor


def Landsat8_QA() -> BitFlagScheme:
    # see https://www.usgs.gov/land-resources/nli/landsat/landsat-collection-1-level-1-quality-assessment-band?
    # qt-science_support_page_related_con=0#qt-science_support_page_related_con
    scheme = BitFlagScheme('Landsat 8 Collection 1 QA band bits')

    p1 = BitFlagParameter('Designated Fill', 0)

    p2 = BitFlagParameter('Terrain Occlusion', 1)

    p3 = BitFlagParameter('Radiometric Saturation', 2, 2)
    p3[0].setName('No bands contain saturation')
    p3[1].setName('1-2 bands contain saturation')
    p3[1].setName('3-4 bands contain saturation')
    p3[1].setName('5 or more bands contain saturation')

    p4 = BitFlagParameter('Cloud', 4)
    p4[1].setColor('grey')

    p5 = BitFlagParameter('Cloud Confidence', 5, 2)
    p5[0].setName('Not Determined')
    p5[1].setName('Low')
    p5[2].setName('Medium')
    p5[3].setName('High')

    p6 = BitFlagParameter('Cloud Shadow Confidence', 7, 2)
    p6[0].setName('Not Determined')
    p6[1].setName('Low')
    p6[2].setName('Medium')
    p6[3].setName('High')

    p7 = BitFlagParameter('Snow/Ice Confidence', 9, 2)
    p7[0].setName('Not Determined')
    p7[1].setName('Low')
    p7[2].setName('Medium')
    p7[3].setName('High')

    p8 = BitFlagParameter('Cirrus Confidence', 11, 2)
    p8[0].setName('Not Determined')
    p8[1].setName('Low')
    p8[2].setName('Medium')
    p8[3].setName('High')

    scheme.mParameters.extend([p1, p2, p3, p4, p5, p6, p7, p8])
    return scheme


def LandsatTM_QA() -> BitFlagScheme:
    scheme = Landsat8_QA()
    scheme.mName = 'Landsat 4-5 Collection 1 QA band bits'
    del scheme.mParameters[7:]
    return scheme


def LandsatMSS_QA() -> BitFlagScheme:
    scheme = Landsat8_QA()
    scheme.mName = 'Landsat 1-5 MSS Collection 1 QA band bits'
    del scheme.mParameters[5:]
    return scheme


def DEPR_FORCE_QAI() -> BitFlagScheme:
    # use color scheme of FORCE OVV overview images
    scheme = BitFlagScheme('FORCE Quality Assurance Information')

    p0 = BitFlagParameter('Valid data', 0)
    p0[0].setName('valid')
    p0[1].setName('no data')

    p1 = BitFlagParameter('Cloud state', 1, 2)
    p1[0].setName('clear')
    p1[1].setValues('less confident cloud', color=QColor(255, 0, 255), isVisible=True)
    p1[2].setValues('confident, opaque cloud', color=QColor(255, 0, 255), isVisible=True)
    p1[3].setValues('cirrus', color=QColor(255, 0, 0), isVisible=True)

    p2 = BitFlagParameter('Cloud shadow', 3, 1)
    p2[1].setValues(color=QColor(0, 255, 255), isVisible=True)

    p3 = BitFlagParameter('Snow', 4, 1)
    p3[1].setValues(color=QColor(255, 255, 0), isVisible=True)

    p4 = BitFlagParameter('Water', 5, 1)
    p4[1].setValues(color=QColor(0, 0, 255), isVisible=False)

    p5 = BitFlagParameter('Aerosol', 6, 2)
    p5[0].setName('estimated')
    p5[1].setName('interpolated')
    p5[2].setName('high')
    p5[3].setName('fill')

    p6 = BitFlagParameter('Subzero', 8)
    p6[1].setValues(color=QColor(34, 177, 76), isVisible=True)

    p7 = BitFlagParameter('Saturation', 9)
    p7[1].setValues(color=QColor(255, 127, 39), isVisible=True)

    p8 = BitFlagParameter('High sun zenith', 10)

    p9 = BitFlagParameter('Illumination', 11, 2)

    p9[0].setName('good')
    p9[1].setName('low')
    p9[2].setName('poor')
    p9[3].setName('shadow')

    p10 = BitFlagParameter('Slope', 13)
    p11 = BitFlagParameter('Water vapor', 14)
    p11[0].setName('measured')
    p11[1].setName('fill')

    scheme.mParameters.extend([p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11])
    return scheme
