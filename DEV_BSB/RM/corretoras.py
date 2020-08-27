"""
Carregar dados de calls de corretoras, recebidas no email de Pricing
"""

from os import path, listdir

import pandas as pd

_ROOT_DIR = r'\\bsbrsp55\Hist_AC\Pricing_Publication\CorretorasParsed'


def load(which, start_date, end_date=None):
    """
    Carrega dados de call das corretoras de determinado período

    Parameters
    ----------
    which: str
        Call das corretoras: NTNB, LTN_NTNF ...
    start_date: date_like
        Data da captura inicial
    end_date: date_like
        Data da captura final (exclusa). Se for 'None'
        captura apenas a data inicial

    Returns
    -------
    pd.DataFrame
    """
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date) if end_date is not None \
        else start_date + pd.DateOffset(days=1)
    if start_date >= end_date:
        raise ValueError('End date must be greater than start date')

    which = which.upper()
    filepath = path.join(_ROOT_DIR, f'{which}.csv')
    if not path.isfile(filepath):
        calls_available = [f.split('.')[0] for f in listdir(_ROOT_DIR)]
        raise ValueError(f'Calls disponíveis: {calls_available}')

    df = pd.read_csv(filepath, sep=';', parse_dates=['DATACAPTURA'])
    df = df.loc[(df['DATACAPTURA'] >= start_date)
                & (df['DATACAPTURA'] < end_date)]
    # parse additional date columns:
    for col in ('MATURITY', 'DATAD2'):
        if col in df.columns:
            df.loc[:, col] = pd.to_datetime(df[col])
    return df


if __name__ == '__main__':
    call = load('NTNB', '2019-10-25')
    print(call)
