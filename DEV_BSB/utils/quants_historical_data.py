

from os import path, scandir
from xml.etree import ElementTree
from functools import lru_cache

import pandas as pd


ROOT_FOLDER = r'\\bsbrsp369\Treasury\Globo\deploy\IBox\PROD\XMLFiles\HistoricalData'


@lru_cache(maxsize=4)
def load_hist(product: str) -> pd.Series:
    """
    Carrega série histórica de dado produto. Retorna
    pd.Series com os valores, indexado por data.
    """
    product = product.lower()
    with open(path.join(ROOT_FOLDER, f'{product}.xml')) as f:
        root = ElementTree.fromstring(f.read())

    df = pd.DataFrame(((a, b) for (a, b) in root), columns=['DATE', 'VALUE'])
    df = df.applymap(lambda v: v.text)
    df = df.astype({'DATE': int, 'VALUE': float})
    # excel date to timestamp:
    df.DATE = df.DATE.apply(lambda v: pd.Timestamp('1899-12-30') + pd.DateOffset(days=v))
    df = df.set_index('DATE')
    return df['VALUE']


load_hist.available = pd.Index([
    v.name.split('.')[0] for v in scandir(ROOT_FOLDER)
    if v.name.endswith('.xml')
])





