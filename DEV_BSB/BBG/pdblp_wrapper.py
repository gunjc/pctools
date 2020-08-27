"""
Useful Bloomberg API functions, wrapping pdblp library's functionality
EXPERIMENTAL!!
"""

# Python
from os import path
from itertools import groupby

# External
import numpy as np
import pandas as pd
import pdblp

# Internal
import pypctools as pct


def bdh_cache(fpath, bcon, tickers, flds, start_date, end_date, **kwargs):
    """
    Consulta a bloomberg por BDH, primeiro contrastando os dados pedidos
    com uma base de dados ("cache"), e requisitando somente aqueles
    que nao estao no cache. Salva os resultados nessa base.

    Parameters
    ----------
    fpath: str
        Caminho do arquivo csv usado como base
    bcon: pdblp.Bcon
        Conexao com a bloomberg, precisa estar startada
    tickers: list
        lista de tickers
    flds: list
        lista de fields
    start_date: date-like
        data inicio do bdh
    end_date: date-like
        data fim do bdh
    kwargs
        kwargs para a funcao pdblp.bdh

    Returns
    -------
    pd.DataFrame
        dataframe com os dados da bloomberg. Nao inclui os dados que
        ja estavam em cache
    """
    expected_cols = ['date', 'ticker', 'field', 'value']
    if not path.isfile(fpath):
        cache_df = pd.DataFrame(columns=expected_cols)
    else:
        cache_df = pd.read_csv(fpath, sep=';', parse_dates=['date'])

    cache_ix = cache_df.set_index(['date', 'ticker', 'field']).index

    # normalize bdh arguments, and construct the query index:
    dates = pct.bday_range(start_date, end_date)
    tickers = [tickers.upper()] if isinstance(tickers, str) else list(map(str.upper, tickers))
    flds = [flds.upper()] if isinstance(flds, str) else list(map(str.upper, flds))
    new_ix = pd.MultiIndex.from_product([
        dates, tickers, flds
    ], names=['date', 'ticker', 'field'])

    # contrast queried index with cached index:
    _intersect_ix = new_ix.intersection(cache_ix)
    diff_ix = new_ix.difference(cache_ix)
    assert len(_intersect_ix) + len(diff_ix) == len(new_ix)
    if len(_intersect_ix) != 0:
        print(f'{len(_intersect_ix)} rows already in cache')

    # override longdata (needed to keep csv in order)
    kwargs['longdata'] = True

    # now we bdh only the diff_ix values:
    pulled_df = pd.DataFrame(columns=expected_cols)
    for date, group in groupby(diff_ix.values, key=lambda tup: tup[0]):
        items = list(group)
        tickers = list(np.unique([t[1] for t in items]))
        flds = list(np.unique([t[2] for t in items]))
        date_str = date.strftime("%Y%m%d")

        for ticker in tickers:
            try:
                temp_df = bcon.bdh(ticker, flds, date_str, date_str, **kwargs)
            except ValueError:
                print(f"invalid security: {ticker}")
                # invalid security error: fill with NaN values
                temp_df = pd.DataFrame(index=range(len(flds)))
                temp_df["date"] = date
                temp_df["ticker"] = ticker
                temp_df["field"] = flds
                temp_df["value"] = np.nan

            temp_df = temp_df.set_index(['date', 'ticker', 'field']).reindex(
                pd.MultiIndex.from_product([
                    [date], [ticker], flds
                ], names=['date', 'ticker', 'field'])
            ).reset_index()

            pulled_df = pd.concat([pulled_df, temp_df], ignore_index=True)

    print('Pulled data:')
    print(pulled_df)

    cache_df = pd.concat([cache_df, pulled_df], ignore_index=True)

    # save to csv:
    cache_df.to_csv(fpath, sep=';', date_format='%Y-%m-%d', index=False)
    print("saved to csv")

    return pulled_df


if __name__ == '__main__':
    # test
    bcon = pdblp.BCon(debug=True, timeout=20_000)
    bcon.start()
    tickers = ["ENEV32@ATIV CORP", "ENEV33@ATIV CORP", "ENEV32@CAPB CORP"]
    flds = ["YLD_YTM_BID", "YLD_YTM_ASK"]
    start_date = "2019-12-09"
    end_date = "2019-12-10"
    fpath = r"M:\PYTEMP\bbg_cache_test1.csv"
    kwargs = {}

    bdh_cache(fpath, bcon, tickers, flds, start_date, end_date, **kwargs)

    bcon.stop()
