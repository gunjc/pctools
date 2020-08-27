"""
Carrega algum tipo de Sensmap
"""

from os import path
import warnings

import numpy as np
import pandas as pd

warnings.simplefilter('always')


def _invert_dict(dikt):
    """
    Recebe um dicionários com itens (key, iterable),
    e inverte de forma que cada item do 'iterable' tenha como
    valor sua key original. Necessário que todos os valores
    de todos os iterable sejam únicos.
    """
    # dupes check (mesmo valores mapeando para mais de uma chave)
    err_msg = 'Mapeamentos inconsistentes / duplicados'
    assert ~pd.Series([v for k in dikt for v in dikt[k]]).duplicated().any(), err_msg

    inv_dikt = dict()
    for key, iterable in dikt.items():
        for item in iterable:
            inv_dikt[item] = key
    return inv_dikt


# -------- constantes -------------

_ROOT_FOLDER = r'\\mscluster34fs\RM_RF\BHA'

# Mapa de Fator_de_Risco para CRV_CODE.
# Preencher manualmente quando necessário.
_RISK_TO_CRVCODE = {
    "PRE": (
        'BRAPRE',
        'BR-IR-BRL-BRBBASACNOR3-REPO',
        'BR-IR-BRL-BRBBDCACNPR8-REPO',
        'BR-IR-BRL-BRBVMFACNOR3-REPO',
        'BR-IR-BRL-BRGGBRACNPR8-REPO',
        'BR-IR-BRL-BRITUBACNPR1-REPO',
        'BR-IR-BRL-BRPDGRACNOR8-REPO',
        'BR-IR-BRL-BRPETRACNPR6-REPO',
        'BR-IR-BRL-BRUSIMACNPA6-REPO',
        'BR-IR-BRL-BRVALEACNPA3-REPO',
        'BR-IR-BRL-PRE_SPREAD-DEPOFUT-CC0',
        'BRAIBOVPRE',
        'BRALTN',
        'BRANTNF',
        'BRASELIC',
        'BR-IR-BRL-BRCSANACNOR6-REPO',
        'BR-IR-BRL-BRCYREACNOR7-REPO',
        'BR-IR-BRL-BROIBRACNOR1-REPO',
        'BR-IR-BRL-BRTAEECDAM10-REPO',
        'BRL :Std',
        'BRL_LTN',
        'BRL_NTNF',
        'BRL_PRE_SPREAD',
        'BRL_SELIC',
        'BRL PRE',
        'BRL SELIC',
        'BR-IR-BRL-BRMRFGACNOR0-REPO',
    ),
    "CONV": (
        'BRL CONV',
        'BRL LTN CONV',
    ),
    "TJLP": (
        'BRL CPN TJLP',
    ),
    "CPNUSD": (
        'DOL FRC',
        'USD FRC (BRAZIL)',
    ),
    "ON_OFF_PRE": (
        'BRL PRE SPREAD',
    ),
    "TR": (
        'BRL CPN TR',
        'BRL TDA'
    ),
    "IPCA": (
        'BRL CUPOM IPCA',
    ),
    "IGPM": (
        'BRL IGPM',
    ),
    "US_RATES": (
        'BRAUSTREA',
        'USD FEDFUND',
        'USD LIBOR 1M',
        'USD LIBOR 3M',
        'USD LIBOR 6M',
        'USD LIBOR 12M',
    ),
    "OUTROS": (
        'MXN TIIE28D',
        'EUR BASSWAP COL',
        'USD BASSWAP COL',
        'EUR FX',
        'JPY STD',
        'ARS :Std',
        'AUD DEPOSWAP 6M',
        'CAD :Std',
        'CHF DEPOSWAP 6M',
        'CLF :Std',
        'CDK :Std',
        'CLP :Std',
        'CNH :Std',
        'CNY :Std',
        'COP :Std',
        'CSU :Std',
        'DCN :Std',
        'DKK :Std',
        'EUR :Std',
        'EUR CALMNY DISC',
        'EUR DEPOSWAP 3M',
        'EUR DEPOSWAP 6M',
        'FSU :Std',
        'GBP DEPOSWAP 6M',
        'HCN :Std',
        'HKD :Std',
        'INR :Std',
        'LEB :Std',
        'MXN :Std',
        'NOK DEPOSWAP 6M',
        'NZD :Std',
        'PCL :Std',
        'PEN :Std',
        'PLN :Std',
        'PMX :Std',
        'RUB :Std',
        'SEK DEPOSWAP 6M',
        'SGD :Std',
        'THB :Std',
        'TRY DEPOSWAP 3M',
        'YCN :Std',
        'YEN :Std',
        'ZAR :Std',
        'USD_CPI_US',
        'XAU :Std',
        'KRW DEPOSWAP 6M',
    ),
    "RISCO FORA DO FVA": (
        'COP_IBR',
        'BRL LFT',
        'BRL NTNB',
        'BRL NTNC',
        'BRL NTNF ZC',
        'BRL OFF',
        'BRE_CPN_CLEAN_FX',
        'CNO :Std',
        'PAR :Std',
    ),
    'PREMIO_NTNF': (
        'BRL NTNF',
    ),
    'PREMIO_LTN': (
        'BRL LTN',
    )
}

# inversão do dict acima
_CRVCODE_TO_RISK = _invert_dict(_RISK_TO_CRVCODE)


def load(which, ref_date, *, raw=False):
    """
    Carrega um arquivo csv de sensmap

    Parameters
    ----------
    which: str
        Subnome do arquivo, e.g. "SENSMAP", "SENSMAP_FVA"
    ref_date: datetime_like
        Data de referência da sensmap
    raw: bool, default False
        Se True retorna a sensmap original. Se False (default), faz um cleanup
        na sensmap e adiciona colunas auxiliares, dependendo do tipo de sensmap.
        Útil para a sensmap fva.

    Returns
    -------
    pd.DataFrame
    """
    # which = 'sensmap_fva'
    # ref_date = '2020-6-17'
    ref_date, which = pd.Timestamp(ref_date), which.upper()
    ref_date_str = ref_date.strftime("%Y%m%d")
    filename = f'BRA_TOT_{ref_date_str}_{which}.csv'

    def find_file():
        # the root folder is a mess. We try to locate the csv file in many
        # possible folders, with a top-down search:
        lookup_chain = (
            # freshest files
            path.join(_ROOT_FOLDER, 'Input', filename),
            # files from month start
            path.join(_ROOT_FOLDER, 'Historico', ref_date_str,
                      ref_date_str, filename),
            # older files
            path.join(_ROOT_FOLDER, 'Historico', str(ref_date.year),
                      ref_date.strftime("%Y%m"), ref_date_str,
                      ref_date_str, filename),
            path.join(_ROOT_FOLDER, 'Historico', str(ref_date.year),
                      ref_date.strftime("%Y-%m"), ref_date_str,
                      ref_date_str, filename)
        )
        for filepath in lookup_chain:
            if path.isfile(filepath):
                print(f'Found {which} file in {path.dirname(filepath)}')
                return filepath

        raise FileNotFoundError(f"Could not find file {filename} anywhere")

    # this avoids pandas dtypewarning because TYPE columns has empty fields
    # interpreted as NaNs
    dtype = {'TYPE': str} if which == 'SENSMAP_FVA' else None
    # read the whole thing
    df = pd.read_csv(find_file(), sep=';', dtype=dtype)

    if raw:
        return df

    # ---- cleaning up the sens and adding info to it ----

    # uppercase columns:
    df.columns = df.columns.str.upper()

    # keep only a bunch useful columns:
    usecols = []
    if which == 'SENSMAP':
        usecols = 'CRITERIA CRV_CODE TENOR_CODE SENS'.split()
    elif which == 'SENSMAP_FVA':
        usecols = 'CRITERIA CRV_CODE TENOR_CODE SENS ' \
                  'PL_INSTRUMENT FAMILY ' \
                  'GRUPO TYPE PORTFOLIO CALL_PUT'.split()

    if usecols:
        new_cols = [v for v in usecols if v in df.columns]
        df = df.loc[:, new_cols]

    if 'CRV_CODE' in df.columns:
        # drop NaNs CRV_CODE's (sujeira, segundo Quixadá,
        # sempre aparece nos 2 últimos dias do mês)
        len_before = len(df)
        df.dropna(subset=['CRV_CODE'], inplace=True)
        n_rows_dropped = len_before - len(df)
        if n_rows_dropped != 0:
            print(f'Dropped {n_rows_dropped} rows with null CRV_CODE field')

        # mapear riscos:
        df['RISK'] = df['CRV_CODE'].map(_CRVCODE_TO_RISK)

        if not df[pd.isna(df.RISK)].empty:
            missings = df[pd.isna(df['RISK'])]['CRV_CODE'].unique()
            # raise warning for missing CRV_CODE to RISK map
            warnings.warn(f'FALTANDO MAPEAMENTO DOS SEGUINTES CRV_CODES '
                          f'P/ RISCO NA SENSMAP: {missings}', stacklevel=2)

    if which == 'SENSMAP_FVA':
        # adicionar campo INST_KEY "familia&grupo&tipo&inst"
        if 'TYPE' in df.columns:
            df['TYPE'] = df['TYPE'].fillna('')  # sometimes TYPE is NaN
            df['INST_KEY'] = df['FAMILY'] + '&' + df['GRUPO'] + '&' \
                             + df['TYPE'] + '&' + df['PL_INSTRUMENT']

        # adicionar campo DESK, a partir do CRITERIA:
        if 'CRITERIA' in df.columns:
            assert 'DESK' not in df.columns

            # definição do mapeamento de CRITERIA para as mesas
            # de acordo com a data. Esse mapeamento muda uma ou duas vezes
            # ao longo do ano.
            if ref_date < pd.Timestamp('2020-01-01'):
                desk_to_criteria = {
                    "ALM": ('ALM',),
                    "ACPM": ('ACPM',),
                    "PT": (
                        "PROPRIETARY TRADING",
                        "PROPRIETARY TRA",  # annoying
                    ),
                    "MM": ("MM RATES", "LIQUIDITY",),
                    "FT": ("FLOW",),
                }
            else:
                # a partir do começo de 2020, as mesas MM e FT tiveram seus CRITERIA mudados:
                desk_to_criteria = {
                    "ALM": ('ALM',),
                    "ACPM": ('ACPM',),
                    "PT": (
                        "PROPRIETARY TRADING",
                        "PROPRIETARY TRA",  # annoying
                    ),
                    "MM": (
                        "MM RATES",
                        # "LIQUIDITY",
                        # Novos CRITERIA: (2020)
                        "NON FLOW DEBEN",
                        "NON FLOW RATES",
                        "NON FLOW VOL EQ",
                        "NON FLOW VOL IR",
                        "LIQUIDITY",
                        "MM BACK BOOK",
                        "COMMODITIES",
                        "ALGO TRADING",
                        "FONDOS",
                        "DEMANDAS BB",
                    ),
                    "FT": (
                        "FLOW FX",
                        "FLOW RATES",
                        "FLOW VOL FX",
                        "FLOW VOL RATES",
                    ),
                }

            criteria_to_desk = _invert_dict(desk_to_criteria)
            df['DESK'] = df['CRITERIA'].map(criteria_to_desk)

            # garantir a soma das sensibilidades mesas da tesouria
            # equivalente ao criteria 'TOTAL TESORERIA', por
            # risco e vértice:
            tes_desks = ['MM', 'FT', 'PT', 'ACPM']
            tes_sens = df.loc[df['CRITERIA'] == 'TOTAL TESORERIA']
            desk_sens = df.loc[df['DESK'].isin(tes_desks)]

            df1 = tes_sens.groupby(['RISK', 'TENOR_CODE'])['SENS'].sum()
            df2 = desk_sens.groupby(['RISK', 'TENOR_CODE'])['SENS'].sum()
            if not np.allclose(df1, df2, rtol=0, atol=1.e-5):
                diff = (df2 - df1).sum()
                warnings.warn("Verificar sensibilidades distorcidas entre mesas"
                              f" e TOTAL TESORERIA, abrindo {diff}", stacklevel=2)

            # garantir quebra correta de market making entre flow e no-flow:
            # mm no flow + mm flow = MarketMaking criteria
            mm = df.loc[df['CRITERIA'] == 'MARKET MAKING']
            mm_flow = df.loc[df['DESK'] == 'FT'].groupby(['RISK', 'TENOR_CODE'])['SENS'].sum()
            mm_noflow = df.loc[df['DESK'] == 'MM'].groupby(['RISK', 'TENOR_CODE'])['SENS'].sum()

            df1 = mm.groupby(['RISK', 'TENOR_CODE'])['SENS'].sum()
            df2 = mm_flow.add(mm_noflow, fill_value=0)
            if not np.allclose(df1, df2, rtol=0, atol=1.e-5):
                diff = (df2 - df1).sum()
                warnings.warn("Verificar sensibilidades MM NO FLOW + MM FLOW != MARKET MAKING, "
                              f"abrindo {diff}", stacklevel=2)

    return df


def _bater_sensmap_sensmapfva(ref_date):
    """Bater as sensibilidades SENSMAP & SENSMAP_FVA da tesouraria"""
    ref_date = '2020-01-31'
    sm = load('SENSMAP', ref_date)
    sfva = load('SENSMAP_FVA', ref_date)

    sm = sm.loc[sm['CRITERIA'] == 'TOTAL TESORERIA']
    sfva = sfva.loc[sfva['CRITERIA'] == 'TOTAL TESORERIA']

    sm_pre = sm.loc[sm['RISK'] == 'PRE']
    sfva_pre = sfva.loc[sfva['RISK'] == 'PRE']

    s1 = sm.groupby(['CRITERIA', 'RISK', 'TENOR_CODE'])['SENS'].sum()
    s2 = sfva.groupby(['CRITERIA', 'RISK', 'TENOR_CODE'])['SENS'].sum()

    s1.sum(level=1) - s2.sum(level=1)
    # (s1 - s2).abs()
    np.allclose(s1, s2, rtol=0, atol=1.e-2)


if __name__ == '__main__':
    # ref_date = '2019-12-23'
    # df_sens = load('SENSMAP', ref_date)
    # df_fva = load('SENSMAP_FVA', ref_date)

    # check entre SENSMAP e SENSMAP_FVA
    date = '2020-01-9'
    sm = load('SENSMAP', date, raw=True)
    sf = load('SENSMAP_FVA', date, raw=True)

    gsm = sm.groupby(['CRITERIA', 'TENOR_CODE'])['SENS'].sum()
    gsf = sf.groupby(['CRITERIA', 'TENOR_CODE'])['SENS'].sum()

    sm.CRITERIA.unique()
    sf.CRITERIA.unique()
    diff = gsf - gsm
    print(
        diff[diff.abs() > 0.01]
    )



