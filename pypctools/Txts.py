"""
Functions for loading published pricing txt files from the network
"""

# Python
from os import path, scandir
import functools
import fnmatch

# External
import pandas as pd


__all__ = ['load_pricing_vertices', 'load_pricing_curve',
           'load_pricing_bond', 'read_currency', 'read_index',
           'load_pricing_tvm']


_ROOT_DIR = r'\\bsbrsp55\Hist_AC\Pricing_Publication'

_SUBFOLDER_MAP = {
    'curves': (r'Curves\ONSHORE',
               r'Curves\OFFSHORE'),
    'vertices': (r'Curves\Vertices\ONSHORE',
                 r'Curves\Vertices\OFFSHORE'),
    'bonds': (r'Bonds\ONSHORE',
              r'Bonds\OFFSHORE'),
    'currency': (r'Currency',),
    'index': (r'Index',),
    'rates': (r'Rates\ONSHORE',
              r'Rates\OFFSHORE'),
    'tvm': (r'TVM',),
    'equities': (r'Equities',),
}


def _easy_txt_rootname(root_fname: str) -> str:
    """Transforms 'ON BRL IPCA' -> 'ON_BRL_IPCA'"""
    return '_'.join(root_fname.strip().upper().split())


def _find_file(subfolders: tuple, filename: str):
    """Returns the filepath of the filename"""
    # search folders:
    for folder in subfolders:
        filepath = path.join(_ROOT_DIR, folder, filename)
        if path.isfile(filepath):
            return filepath

    # old files:
    curve_date = filename.split('.')[0].split('_')[-1]
    yyyymm = curve_date[:6]
    for folder in subfolders:
        filepath = path.join(_ROOT_DIR, folder, yyyymm, filename)
        if path.isfile(filepath):
            return filepath

    raise FileNotFoundError(f"Couldn't find {filename}.")


def _list_available_files(subfolders, date):
    """
    Searches the subfolders and returns a list of available
    files with the given date.
    """
    file_pat = f"*_{pd.Timestamp(date).strftime('%Y%m%d')}.txt"

    files = []
    for subfolder in subfolders:
        folder = path.join(_ROOT_DIR, subfolder)
        files += [f.name.rsplit('_', 1)[0]
                  for f in fnmatch.filter(scandir(folder), file_pat)]

    return files


def load_pricing_vertices(curve_name, ref_date):
    """
    Load a vertices txt

    Parameters
    ----------
    curve_name: str
        Vertices base filename
    ref_date: date_like
        Reference date

    Returns
    -------
    pd.DataFrame

    """
    curve_name = _easy_txt_rootname(curve_name)
    ref_date_str = pd.Timestamp(ref_date).strftime("%Y%m%d")

    filename = f'{curve_name}_{ref_date_str}.txt'
    filepath = _find_file(_SUBFOLDER_MAP['vertices'], filename)

    return pd.read_csv(
        filepath,
        delimiter=';',
        dtype={'RATE': float},
        parse_dates=['START_DATE', 'END_DATE'],
        date_parser=lambda d: pd.to_datetime(d, format='%d/%m/%Y'),
    )


def load_pricing_curve(curve_name, ref_date):
    """
    Load a curve txt

    Parameters
    ----------
    curve_name: str
        Curve base filename
    ref_date: date_like
        reference date

    Returns
    -------
    pd.Dataframe
        A dataframe indexed by 'DATE'
    """
    curve_name = _easy_txt_rootname(curve_name)
    ref_date_str = pd.Timestamp(ref_date).strftime("%Y%m%d")

    filename = f'{curve_name}_{ref_date_str}.txt'
    filepath = _find_file(_SUBFOLDER_MAP['curves'], filename)

    return pd.read_csv(
        filepath,
        sep=';',
        dtype={'DISC_FACTOR': float, 'ACCUM_FACTOR': float, 'RATE': float},
        parse_dates=['DATE'],
        date_parser=lambda d: pd.to_datetime(d, format='%d/%m/%Y'),
        index_col='DATE',
    )


def load_pricing_bond(bond_file, ref_date):
    """
    Load a bond txt

    Parameters
    ----------
    bond_file: str
        Bond base filename
    ref_date: date_like
        reference date

    Returns
    -------
    pd.Dataframe
    """
    bond_file = _easy_txt_rootname(bond_file)
    ref_date_str = pd.Timestamp(ref_date).strftime("%Y%m%d")

    filename = f'{bond_file}_{ref_date_str}.txt'
    filepath = _find_file(_SUBFOLDER_MAP['bonds'], filename)

    # load bond file
    df = pd.read_csv(filepath, sep=';')

    # parse dates (if needed):
    if 'MATURITY' in df.columns:
        df['MATURITY'] = pd.to_datetime(df['MATURITY'], format='%d/%m/%Y')

    return df


def read_currency(cur_pair, ref_date, which='SPOT'):
    """
    Get a currency's exchange rate

    Parameters
    ----------
    cur_pair: str
        The currency pair, e.g. 'USDBRL', 'EURBRL', 'EURUSD' etc.
    ref_date: date_like
        Reference date
    which: {'SPOT', 'SPOT_D0', 'PTAX'}, default 'SPOT'
        One of the following:
        * 'SPOT': exchange rate for d2 delivery (default);
        * 'SPOT_DO': exchange rate for d0 delivery;
        * 'PTAX': PTAX ask rate.

    Returns
    -------
    float
    """
    cur_pair = cur_pair.upper()
    ref_date_str = pd.Timestamp(ref_date).strftime("%Y%m%d")
    which = which.upper()

    filename = f'FX_{which}_{ref_date_str}.txt'
    filepath = _find_file(_SUBFOLDER_MAP['currency'], filename)

    df = pd.read_csv(
        filepath, sep=';', index_col='CURRENCY', squeeze=True
    )
    return float(df.at[cur_pair])


def read_index(ix_name, ref_date):
    """
    Reads an index rate at given date.
    Available indices:

    Interest:
        CDI, SELIC, IDI1, IDI2, ISE, ITJLP, TR
    Inflation:
        IPCA, IPCA_PRORATA, IPCA_RATE,
        IGPM, IGPM_PRORATA, IGPM_RATE,
        INCCM, INCCM_PRORATA, INCCM_RATE,
    Equity indices:
        CAC, DAX, FTSE, FTSE_MIB, IB5M11, IBEX35, IBOV,
        IBX50, IMAB11, IRFM11, MXWO, S&P500, STOXX50

    Parameters
    ----------
    ix_name: str
    ref_date: date_like
        Reference date

    Returns
    -------
    float
        Index rate
    """
    ix_name = ix_name.upper()
    ref_date_str = pd.Timestamp(ref_date).strftime("%Y%m%d")

    # Index
    if ix_name in ('IDI1', 'IDI2', 'ISE', 'ITJLP', 'TR'):
        filename = f'INDEX_ON_{ref_date_str}.txt'
        filepath = _find_file(_SUBFOLDER_MAP['index'], filename)
        s = pd.read_csv(filepath, sep=';', index_col='NAME', squeeze=True)
        return s.at[ix_name]

    # Inflation:
    if ix_name.startswith(('IGPM', 'IPCA', 'INCCM')):
        ix_row, _, ix_type = ix_name.partition('_')
        col = {
            '': 'LAST_VALUE',
            'PRORATA': 'PRORATED_INDEX',
            'RATE': 'VARIATION_FORECAST',
        }.get(ix_type)
        if col is not None:
            filename = f'ON_INFLATION_{ref_date_str}.txt'
            filepath = _find_file(_SUBFOLDER_MAP['rates'], filename)
            df = pd.read_csv(filepath, sep=';', index_col='INDEX_NAME')
            return df.at[ix_row, col]

    # Overnight
    if ix_name in ('CDI', 'SELIC'):
        filename = f'ON_OVERNIGHT_{ref_date_str}.txt'
        filepath = _find_file(_SUBFOLDER_MAP['rates'], filename)
        s = pd.read_csv(filepath, sep=';', index_col='NAME', squeeze=True)
        return s.at[ix_name]

    if ix_name in ('CAC', 'DAX', 'FTSE', 'FTSE_MIB', 'IB5M11', 'IBEX35', 'IBOV',
                   'IBX50', 'IMAB11', 'IRFM11', 'MXWO', 'S&P500', 'STOXX50'):
        filename = f'INDEX_SPOT_{ref_date_str}.txt'
        filepath = _find_file(_SUBFOLDER_MAP['equities'], filename)
        s = pd.read_csv(filepath, sep=';', index_col='NAME', squeeze=True)
        return s.at[ix_name]

    raise ValueError(f"Unknown index {ix_name}")


def load_pricing_tvm(ref_date):
    """
    Load TVM txt w/ corporate bonds data

    .. versionadded:: 1.3

    Parameters
    ----------
    ref_date: date_like
        reference date

    Returns
    -------
    pd.Dataframe
    """
    ref_date_str = pd.Timestamp(ref_date).strftime("%Y%m%d")
    filename = f'TVM_{ref_date_str}.txt'
    filepath = _find_file(_SUBFOLDER_MAP['tvm'], filename)

    # load bond file
    df = pd.read_csv(filepath, sep=';')
    df.columns = df.columns.str.upper()

    # parse dates:
    if 'NTNB_REF' in df.columns:
        df['NTNB_REF'] = pd.to_datetime(
            df['NTNB_REF'], format='%d-%b-%y', errors='coerce'
        )

    return df.set_index('NAME', verify_integrity=True)


# apply useful 'available' function attribute to txt loading functions:

load_pricing_vertices.available = functools.partial(
    _list_available_files, _SUBFOLDER_MAP['vertices']
)

load_pricing_curve.available = functools.partial(
    _list_available_files, _SUBFOLDER_MAP['curves']
)

load_pricing_bond.available = functools.partial(
    _list_available_files, _SUBFOLDER_MAP['bonds']
)
