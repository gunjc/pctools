
import unittest

import numpy as np
import pandas as pd

from pypctools.Calendar import bdbetween
from Curve_bkp import Curve, rate2fct, fct2rate
from pypctools.Txts import load_pricing_curve


class TestTxtCurves(unittest.TestCase):
    """
    Testing if curve txt interpolated by pctools.xll
    is the same as interpolated by pypctools
    """
    def test_on_brl(self):
        """Testar a curva PRÉ"""
        # sample a few on_brl curves
        ref_dates = ['2019-08-30', '2018-12-31', '2019-08-01']
        cparams = dict(interp_method='EXP', compounding='YIELD', day_count='BUS/252', cal='BRL')
        fparams = dict(compounding='YIELD', day_count='BUS/252', cal='BRL')

        # test interpolated rates, the accum_factors, bdbetween, and fct2rate
        for ref_date in ref_dates:
            df = load_pricing_curve('ON_BRL', ref_date).drop(pd.Timestamp(ref_date))
            curve = Curve.from_vertices_txt('ON_BRL', ref_date, **cparams)

            df['PY_RATE'] = curve.interp(df.index)
            self.assertTrue(np.allclose(df['RATE'], df['PY_RATE'],
                                        rtol=0, atol=1.e-13))

            df['PY_ACCUM_FACTOR'] = rate2fct(df['PY_RATE'], ref_date, df.index, **fparams)
            self.assertTrue(np.allclose(df['ACCUM_FACTOR'], df['PY_ACCUM_FACTOR'],
                                        rtol=0, atol=1.e-13))

            df['PY_BD'] = bdbetween(ref_date, df.index)
            self.assertTrue(df['BD'].equals(df['PY_BD']))

            df['PY_F2R'] = fct2rate(df['PY_ACCUM_FACTOR'], ref_date, df.index, **fparams)
            self.assertTrue(np.allclose(df['RATE'], df['PY_F2R'],
                                        rtol=0, atol=1.e-13))

    def test_off_aud(self):
        ref_dates = ['2019-08-30', '2018-12-31', '2019-08-01']
        cparams = dict(interp_method='LIN', compounding='YIELD', day_count='ACT/365', cal=None)
        fparams = dict(compounding='YIELD', day_count='ACT/365', cal=None)

        # test interpolated rates, the accum_factors and term
        for ref_date in ref_dates:
            df = load_pricing_curve('OFF_AUD', ref_date).iloc[3:]
            curve = Curve.from_vertices_txt('OFF_AUD', ref_date, **cparams)

            df['PY_RATE'] = curve.interp(df.index)
            self.assertTrue(np.allclose(df['RATE'], df['PY_RATE'],
                                        rtol=0, atol=1.e-13))

            df['PY_ACCUM_FACTOR'] = rate2fct(df['PY_RATE'], ref_date, df.index, **fparams)
            self.assertTrue(np.allclose(df['ACCUM_FACTOR'], df['PY_ACCUM_FACTOR'],
                                        rtol=0, atol=1.e-13))

            df['PY_TERM'] = (df.index - pd.Timestamp(ref_date)).days
            self.assertTrue(df['TERM'].equals(df['PY_TERM']))

            df['PY_F2R'] = fct2rate(df['PY_ACCUM_FACTOR'], ref_date, df.index, **fparams)
            self.assertTrue(np.allclose(df['RATE'], df['PY_F2R'],
                                        rtol=0, atol=1.e-13))

    def test_off_on_conv_ndf(self):
        ref_dates = ['2019-08-30', '2018-12-31', '2019-08-01']
        cparams = dict(interp_method='LIN', compounding='LINEAR', day_count='ACT/360', cal=None)
        fparams = dict(compounding='LINEAR', day_count='ACT/360', cal=None)

        # test interpolated rates, the accum_factors and term
        for ref_date in ref_dates:
            ref_date = pd.Timestamp(ref_date)
            df = load_pricing_curve('OFF_ON_CONV_NDF', ref_date).drop(ref_date)
            curve = Curve.from_vertices_txt('OFF_ON_CONV_NDF', ref_date, **cparams)

            df['PY_RATE'] = curve.interp(df.index)
            self.assertTrue(np.allclose(df['RATE'], df['PY_RATE'],
                                        rtol=0, atol=1.e-13))

            df['PY_ACCUM_FACTOR'] = rate2fct(df['PY_RATE'], ref_date, df.index, **fparams)
            self.assertTrue(np.allclose(df['ACCUM_FACTOR'], df['PY_ACCUM_FACTOR'],
                                        rtol=0, atol=1.e-13))

            df['PY_TERM'] = (df.index - ref_date).days
            self.assertTrue(df['TERM'].equals(df['PY_TERM']))




