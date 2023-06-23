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
import json
import unittest

from bitflagrenderer.core.bitflagmodel import BitFlagModel
from bitflagrenderer.core.bitflagscheme import BitFlagScheme, BitFlagParameter
from qgis.PyQt.QtCore import Qt, QMimeData, QModelIndex
from qps.testing import start_app
from tests.src.bitflagtests import BitFlagTestCases

start_app()


class BitFlagModelTests(BitFlagTestCases):

    def test_bitflagmodel(self):
        model = BitFlagModel()

        p1 = BitFlagParameter('p1', 1)
        p2 = BitFlagParameter('p2', 3, 2)
        self.assertTrue(model.addFlagParameter(p1))
        self.assertFalse(model.addFlagParameter(p1))
        self.assertTrue(len(model) == 1)

        self.assertTrue(model.addFlagParameter(p2))
        self.assertTrue(len(model) == 2)

        idx1 = model.parameter2index(p1)
        idx2 = model.parameter2index(p2)

        self.assertEqual(idx1.internalPointer(), p1)
        self.assertEqual(idx2.internalPointer(), p2)

        md: QMimeData = model.mimeData([idx1, idx2])

        parameters = BitFlagParameter.fromMimeData(md)
        self.assertTrue(len(parameters) == 2)
        for p in parameters:
            self.assertIsInstance(p, BitFlagParameter)
        self.assertEqual(parameters[0], p1)
        self.assertEqual(parameters[1], p2)

        m2 = BitFlagModel()
        self.assertTrue(m2.canDropMimeData(md, Qt.CopyAction, 0, 0, QModelIndex()))
        self.assertTrue(m2.canDropMimeData(md, Qt.MoveAction, 0, 0, QModelIndex()))

        self.assertEqual(len(m2), 0)
        self.assertTrue(m2.dropMimeData(md, Qt.CopyAction, 0, 0, QModelIndex()))
        self.assertEqual(len(m2), 2)

        for i, p in enumerate(parameters):
            self.assertEqual(m2[i], p)

    def test_bitflagscheme(self):

        scheme1: BitFlagScheme = self.createBitFlagScheme()
        scheme2 = scheme1.clone()

        self.assertEqual(scheme1, scheme2)
        scheme2.setCombineFlags(True)

        self.assertNotEqual(scheme1, scheme2)

        schemes = [scheme1, scheme2]

        for scheme in schemes:
            self.assertIsInstance(scheme, BitFlagScheme)
            # test mimedata / xml serialization
            md: QMimeData = scheme.mimeData()
            scheme2 = BitFlagScheme.fromMimeData(md)

            self.assertEqual(scheme, scheme2)
            self.assertNotEqual(id(scheme), id(scheme2))

            # test json / STAC-like serialization
            jsn = scheme.json()
            self.assertIsInstance(jsn, str)
            scheme3 = BitFlagScheme.fromJson(jsn)
            self.assertEqual(scheme, scheme3)

            d = json.loads(jsn)
            self.assertIsInstance(d, dict)


if __name__ == '__main__':
    unittest.main()
