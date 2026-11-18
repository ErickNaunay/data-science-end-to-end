import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from sklearn.dummy import DummyRegressor
from src.pipeline import dividir, pliegues, crear_pipeline, interpolar_huecos, derivar, FEATURES, FEATURES_LINEALES, MESES_OBJETIVO
import numpy as np
class Temporal(unittest.TestCase):
    def test_objetivo_cruza_corte(self):
        d=pd.DataFrame({'mes_objetivo':pd.PeriodIndex(['2023-12','2024-01'],freq='M')})
        a,b=dividir(d); self.assertEqual(len(a),1); self.assertEqual(len(b),1)
    def test_meses_no_se_mezclan(self):
        meses=pd.period_range('2010-01',periods=40,freq='M')
        d=pd.DataFrame({'anio_mes':[int(m.strftime('%Y%m')) for m in meses for _ in range(3)]})
        for tr,va in pliegues(d):
            self.assertLess(d.iloc[tr].anio_mes.max(),d.iloc[va].anio_mes.min())
            self.assertFalse(set(d.iloc[tr].anio_mes)&set(d.iloc[va].anio_mes))
    def test_imputador_no_ve_prueba(self):
        X=pd.DataFrame({c:[1.,2.,None] for c in FEATURES}); p=crear_pipeline(DummyRegressor()); p.fit(X,[0,1,0])
        med=p.named_steps['preparar'].named_transformers_['numericas'].named_steps['imputar'].statistics_.copy()
        p.predict(pd.DataFrame({c:[1e9,None] for c in FEATURES}))
        self.assertTrue((med==1.5).all())
        self.assertTrue((med==p.named_steps['preparar'].named_transformers_['numericas'].named_steps['imputar'].statistics_).all())
    def test_interpola_solo_huecos_intermedios(self):
        d=pd.DataFrame({'accion_key':[1]*5+[2]*2,'anio_mes':[201001,201002,201003,201004,201005,201001,201002],
                        'vol_21d':[np.nan,1.,np.nan,3.,np.nan,5.,np.nan]})
        r=interpolar_huecos(d,['vol_21d']).set_index(['accion_key','anio_mes']).vol_21d
        self.assertEqual(r[(1,201003)],2.)
        self.assertTrue(np.isnan(r[(1,201001)]) and np.isnan(r[(1,201005)]) and np.isnan(r[(2,201002)]))
    def test_interpolacion_no_cruza_el_corte(self):
        d=pd.DataFrame({'accion_key':[1]*3,'anio_mes':[202310,202311,202312],'vol_21d':[1.,np.nan,3.],
                        'mes_objetivo':pd.PeriodIndex(['2023-11','2023-12','2024-01'],freq='M')})
        a,b=dividir(d)
        self.assertTrue(np.isnan(a.set_index('anio_mes').vol_21d[202311]))
    def test_dispersion_solo_usa_el_mes(self):
        d=pd.DataFrame({'anio_mes':[202001]*3+[202002]*2,'ret_log_mes':[0.,.1,.2,5.,7.]})
        r=derivar(d)
        self.assertAlmostEqual(r.dispersion_mes.iloc[0],0.1)
        self.assertAlmostEqual(r.dispersion_mes.iloc[3],np.std([5.,7.],ddof=1))
    def test_mes_calendario_del_objetivo(self):
        r=derivar(pd.DataFrame({'anio_mes':[202012,202101],'ret_log_mes':[0.,0.]}))
        self.assertEqual(r[MESES_OBJETIVO].iloc[0].sum(),0)          # objetivo enero: referencia
        self.assertEqual(r.mes_obj_02.iloc[1],1.)
    def test_lineales_sin_redundantes(self):
        self.assertEqual(len(FEATURES)-len(FEATURES_LINEALES),4)
if __name__=='__main__': unittest.main()
