"""
Helper functions
"""

from typing import Union, List

import pandas as pd


__all__ = ['KEY_COLS', 'mxname_to_mktname', 'mktname_to_mxname',
           'dead_filter', 'portfolio_filter', 'expired_filter']

# na maioria dos casos, essas colunas são as mais usadas do datamart:
KEY_COLS = [
    'CONTRACTREFERENCE',
    'INSTRUMENT',
    'PORTFOLIO',
    'COUNTERPART',
    'BUYSELL',
    'LIVEQUANTITY',
    'TRNDATE',
    'MSYSDATE',
    'DATEPERIODEXPIRYDATE',
    'DISCOUNTEDMARKETVALUE',
]


# --------- Name conversions for debentures/CRIs/CRAs -----------

def mxname_to_mktname(mxname: str) -> str:

    # Debentures:
    if mxname.startswith('BRL DEB '):
        return mxname.split()[-1]

    # CRI's. Obs: there's an annoying 'BRL CRI 17F0023368' that don't follow
    # the name pattern 'BRL CRIXXXXXXXXXX'. Some others also do that:
    if mxname.startswith('BRL CRI'):
        cris_zoados = ['BRL CRI 17F0023368', 'BRL CRI 12K0035326', 'BRL CRI 16L0074884']
        if mxname in cris_zoados:
            return mxname.split()[-1]
        return mxname.split()[1][3:]

    # CRA's:
    if mxname.startswith('BRL CRA'):
        return mxname.split()[1]

    # Fallback
    return mxname


def mktname_to_mxname(mktname: str) -> str:

    # Debentures:
    if len(mktname) == 6:
        return f'BRL DEB {mktname}'

    # CRI's. Obs: there's an annoying 'BRL CRI 17F0023368' that don't follow
    # the name pattern 'BRL CRI XXXXXXXXXX'. Cadastros zoados no Murex
    if len(mktname) == 10:
        cris_zoados = ['17F0023368', '12K0035326', '16L0074884']
        if mktname in cris_zoados:
            return f'BRL CRI {mktname}'
        return f'BRL CRI{mktname}'

    # CRA's:
    if len(mktname) == 11:
        return f'BRL {mktname}'

    # Fallback
    return mktname


# ------------ datamart's dataframe piping methods --------------


def dead_filter(df: pd.DataFrame):
    """
    Clears rows where STATUSLIVEMKT_OPDEAD == 'DEAD' from
    given dataframe
    """
    if 'STATUSLIVEMKT_OPDEAD' not in df.columns:
        print(f'No STATUSLIVEMKT_OPDEAD column!')
        return df
    return df.loc[df['STATUSLIVEMKT_OPDEAD'] != 'DEAD']


def portfolio_filter(df: pd.DataFrame, portfolios: Union[str, List[str]]):
    """
    Select rows from dataframe by the given portfolio(s)
    """
    if 'PORTFOLIO' not in df.columns:
        print(f'No PORTFOLIO column!')
        return df

    if isinstance(portfolios, str):
        portfolios = [portfolios]
    return df.loc[df['PORTFOLIO'].isin(portfolios)]


def expired_filter(df: pd.DataFrame, ref_date):
    """
    Remove rows with expired instruments ( < ref_date )
    """
    if 'DATEPERIODEXPIRYDATE' not in df.columns:
        print(f'No DATEPERIODEXPIRYDATE column!')
        return df

    ref_date = pd.Timestamp(ref_date)
    return df.loc[df['DATEPERIODEXPIRYDATE'] >= ref_date]
