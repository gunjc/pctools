"""
Puxa séries temporais do webservice do BACEN
"""

# Python
import json
from functools import lru_cache
from collections import defaultdict
from lxml import etree

# External
import requests
from requests_html import HTMLSession
import pandas as pd


__all__ = ['get_series', 'expect_ipca_acum_12m', 'expect_ipca_mensal_1y']


# requires url's and uri's
soapenv = 'http://schemas.xmlsoap.org/soap/envelope/'
xsd = 'http://www.w3.org/2001/XMLSchema'
xsi = 'http://www.w3.org/2001/XMLSchema-instance'
url_webservice = 'https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS'


def _send_request(cod, st_date, end_date):
    """Constructs the XML for request and returns the XML response in bytes"""
    # Preparing the XML to send:
    env = '''<?xml version="1.0" encoding="utf-8"?>'''
    env += '''<soapenv:Envelope xmlns:soapenv="{}" xmlns:xsd="{}" xmlns:xsi="{}">'''.format(soapenv, xsd, xsi)
    env += ''' <soapenv:Body>'''
    env += ''' <getValoresSeriesXML xmlns="{}">'''.format(url_webservice)
    env += ''' <codigosSeries><item>{}</item></codigosSeries>'''.format(cod)
    env += ''' <dataInicio>{}</dataInicio>'''.format(st_date)
    env += ''' <dataFim>{}</dataFim>'''.format(end_date)
    env += ''' </getValoresSeriesXML>'''
    env += ''' </soapenv:Body>'''
    env += '''</soapenv:Envelope>'''
    headers = {'soapAction': "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS/getValoresSeriesXML"}
    with HTMLSession(mock_browser=False) as session:
        r = session.post(url_webservice + '?method=getValoresSeriesXML', data=env, headers=headers)
    return r.content


def _parse_xml(xml_str):
    """Parses XML response and returns a dataframe with the content"""
    root = etree.fromstring(xml_str)
    xml_return = root.xpath('// getValoresSeriesXMLReturn')
    series = etree.fromstring(bytes(xml_return[0].text, encoding='ISO-8859-1'))
    data = defaultdict(list)
    for item in series[0]:
        for el in item.getchildren():
            data[el.tag].append(el.text)

    df = pd.DataFrame.from_dict(data)
    # df['DATA'] = [pd.Timestamp.strptime(d, "%d/%m/%Y").date() for d in dates]
    # df['VALOR'] = [float(v) for v in values]
    return df


def _test():
    # INPUTS: CODE, START DATE, END DATE
    # cod = 11
    cod = 254
    st_date = '28/02/2019'
    end_date = '31/05/2019'
    xml_str = _send_request(cod, st_date, end_date)
    df = _parse_xml(xml_str)
    return df


def get_series(cod: int, from_, to) -> pd.DataFrame:
    """
    Busca a série no SGS do Bacen
    :param cod: int. Código do produto
    :param from_: Start date
    :param to: End date
    :return: pandas dataframe. A quantidade de colunas varia de código para código
    """
    from_ = pd.Timestamp(from_)
    to = pd.Timestamp(to)
    if not to >= from_:
        raise ValueError('Reversed dates')
    xml_str = _send_request(cod, from_.strftime("%d/%m/%Y"), to.strftime("%d/%m/%Y"))
    df = _parse_xml(xml_str)
    return df


# ----- Sistema de Expectativas: ---------


@lru_cache(maxsize=32)
def _bc_sist_expectativas(which, **filters):
    """
    Consulta à API JSON do BC de expectativas de mercado. Em desenvolvimento
        -> Feb 19, 2020: versão inicial p/ FVA de IPCA curto prazo

    Parameters
    ----------
    which: str
        'ExpectativasMercadoInflacao12Meses'
    filters:
        filter parameters

    Returns
    -------
    List
        Lista de dicts, com os dados consultados

    Notes
    -----
    P/ desenvolvimento, mais informações sobre a API nos links:
    https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/documentacao
    https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/swagger-ui2#!/default/ExpectativaMercadoMensais
    https://dadosabertos.bcb.gov.br/dataset/expectativas-mercado/resource/65d9b1b0-d13f-4d5c-b8fa-28c4bf27106b?inner_span=True
    """
    # transformar o dict de filtros em url string:
    # obs: espaços = %20 e single quotes (') = %27
    filter_url = '%20and%20'.join(f"""{k}%20eq%20%27{v.replace(' ', '%20')}%27""" for k, v in filters.items())
    url = f'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/{which}?$format=json&$filter={filter_url}'
    try:
        r = requests.get(url)
    except requests.exceptions.ProxyError as e:
        msg = f'Erro normal de proxy. Tentar de novo ou acessar manualmente a url {url}'
        raise type(e)(msg) from e

    jstr = r.text
    jresp = json.loads(jstr)['value']
    return jresp
    # df = pd.DataFrame(jresp, index=[0])


def expect_ipca_acum_12m(ref_date) -> pd.Series:
    """Estatísticas da expectativa de IPCA acumulado nos próximos 12 meses"""
    ref_date = pd.Timestamp(ref_date)
    which = 'ExpectativasMercadoInflacao12Meses'
    filters = {
        'Indicador': 'IPCA',
        'Data': ref_date.strftime("%Y-%m-%d"),
        'Suavizada': 'N',
    }
    jresp = _bc_sist_expectativas(which, **filters)[0]
    return pd.Series(jresp, name=ref_date)


def expect_ipca_mensal(ref_date) -> pd.DataFrame:
    """
    Estatísticas de expectativa do IPCA mês a mês
    """
    ref_date = pd.Timestamp(ref_date)
    which = 'ExpectativaMercadoMensais'
    filters = {
        'Indicador': 'IPCA',
        'Data': ref_date.strftime("%Y-%m-%d"),
    }
    # read dict response as dataframe
    jresp = _bc_sist_expectativas(which, **filters)
    df = pd.DataFrame(jresp)

    # clean frame & checks:
    assert (df['Indicador'] == 'IPCA').all(), 'Erro indicador buscado'
    # campo baseCalculo que aparentemente as consultas no site pegam apenos o igual a 0
    # (mais info sobre baseCalculo no link de documentação)
    df = df.loc[df['baseCalculo'] == 0]
    # ordenar por data ref de IPCA
    df['DataReferencia'] = pd.to_datetime(df['DataReferencia'], format='%m/%Y')
    df['Data'] = pd.to_datetime(df['Data'], format='%Y-%m-%d')
    assert (df['Data'] == ref_date).all(), 'Erro data ref buscada'
    df.set_index('DataReferencia', verify_integrity=True, inplace=True)
    # sort:
    df.sort_index(inplace=True)
    return df


def expect_igpm_mensal(ref_date) -> pd.DataFrame:
    """
    Estatísticas de expectativa do IGP-M mês a mês
    """
    ref_date = pd.Timestamp(ref_date)
    which = 'ExpectativaMercadoMensais'
    filters = {
        'Indicador': 'IGP-M',
        'Data': ref_date.strftime("%Y-%m-%d"),
    }
    # read dict response as dataframe
    jresp = _bc_sist_expectativas(which, **filters)
    df = pd.DataFrame(jresp)

    # clean frame & checks:
    assert (df['Indicador'] == 'IGP-M').all(), 'Erro indicador buscado'
    # campo baseCalculo que aparentemente as consultas no site pegam apenos o igual a 0
    # (mais info sobre baseCalculo no link de documentação)
    df = df.loc[df['baseCalculo'] == 0]
    # ordenar por data ref de IPCA
    df['DataReferencia'] = pd.to_datetime(df['DataReferencia'], format='%m/%Y')
    df['Data'] = pd.to_datetime(df['Data'], format='%Y-%m-%d')
    assert (df['Data'] == ref_date).all(), 'Erro data ref buscada'
    df.set_index('DataReferencia', verify_integrity=True, inplace=True)
    # sort:
    df.sort_index(inplace=True)
    return df


if __name__ == '__main__':
    pass
    # wsdl = r'https://www3.bcb.gov.br/sgspub/JSP/sgsgeral/FachadaWSSGS.wsdl'
    # from SOAPpy import SOAPProxy
    # from SOAPpy import WSDL
    # r = WSDL.Proxy(wsdl)
    # print r.methods
