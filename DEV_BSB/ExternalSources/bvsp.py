"""
Script para baixar os ajustes de pregão da BMF da internet,
salvar na rede e carregar os dados
"""

from os import path

import pandas as pd
from requests_html import HTMLSession, HTML


__all__ = ['load_ajustes_bmf']


# ------- Main Class -----------------------------------------

class AjustesBMF:
    root_folder = r'\\bsbrsp1152\RM_LE\Curves\Feeders\Bovespa\AjustesPregao'

    def __init__(self, ref_date):
        self.ref_date = pd.Timestamp(ref_date)
        self.ref_date_str = self.ref_date.strftime("%Y%m%d")
        # nome do arquivo CSV na rede:
        self.filename = f'ajustes_bmf_{self.ref_date_str}.csv'
        self.filepath = path.join(self.root_folder, self.filename)

    def _download(self) -> HTML:
        """
        Baixa os ajustes do pregão da internet e retorna o HTML correspondente
        """
        data_url = r'http://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/' \
                   r'lum-ajustes-do-pregao-ptBR.asp'
        payload = {"dData1": self.ref_date.strftime('%d/%m/%Y')}
        with HTMLSession(mock_browser=True) as session:
            r = session.post(data_url, payload)
        r.raise_for_status()
        print(f'AjustesBMF de {self.ref_date_str} baixado da internet')
        return r.html

    def _parse_html(self, html):
        table = html.find('table#tblDadosAjustes')[0]
        df = pd.read_html(table.html, thousands='.', decimal=',')[0]
        df.Mercadoria.fillna(method='ffill', inplace=True)
        return df

    def _save_to_network_dir(self, df):
        df.to_csv(self.filepath, sep=';', index=False)
        print(f'Salvo {self.filename} em {self.root_folder}')

    def load(self) -> pd.DataFrame:
        if path.isfile(self.filepath):
            print(f'{self.filename} carregado da rede')
            return pd.read_csv(self.filepath, sep=';')

        df = self._parse_html(self._download())
        self._save_to_network_dir(df)
        return df


# ------- Convenience API ------------------------------

def load_ajustes_bmf(ref_date):
    """
    Carrega dataframe com os ajustes BMF de determinada data
    """
    return AjustesBMF(ref_date).load()

