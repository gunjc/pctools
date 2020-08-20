"""
Teste. Comparação entre os calendários IBox e original PCTools.xll
"""

import datetime as dt
from xml.etree import ElementTree
from os import path

# External
import numpy as np
import pandas as pd


def xldate_to_datetime(xldate):
    """
    Transforms an integer date represented by MS Excel to python's datetime.
    Function mostly copied from xlrd's function "xldate_as_datetime" so
    we don't need to depend on this external library. Used by default with
    the 'datemode' parameter set to 0.

    Parameters
    ----------
    xldate: int
        The Excel date number

    Returns
    -------
    dt.date
        Python's date representation
    """
    # The integer part of the Excel date stores
    # the number of days since the epoch
    days = int(xldate)

    # Set the epoch
    if days < 60:
        epoch = dt.datetime(1899, 12, 31)  # epoch_1900
    else:
        # Workaround Excel 1900 leap year bug by adjusting the epoch.
        epoch = dt.datetime(1899, 12, 30)  # epoch_1900_minus_1

    return (epoch + dt.timedelta(days)).date()


def ibox_holidays(cal):
    folder = r'G:\Globo\deploy\IBox\PROD\XMLFiles\Calendars'
    with open(path.join(folder, f'{cal}.xml')) as f:
        data = f.read()
    root = ElementTree.fromstring(data)
    holidays = np.array([xldate_to_datetime(int(child.text))
                         for child in root], dtype='datetime64[D]')
    return np.busdaycalendar(holidays=holidays)


def pctools_holidays(cal):
    folder = r'C:\Users\t716584\PycharmProjects\DEV_pypctools\Calendars_PCTools_xll_original'
    with open(path.join(folder, f'{cal}.xml')) as f:
        data = f.read()
    root = ElementTree.fromstring(data)
    holidays = np.array([xldate_to_datetime(int(child.text))
                         for child in root], dtype='datetime64[D]')
    return np.busdaycalendar(holidays=holidays)


c = 'EUR'
i = ibox_holidays(c).holidays
p = pctools_holidays(c).holidays
assert (p == np.sort(p)).all()
assert (i == np.sort(i)).all()
set(i) - set(p)
set(p) - set(i)
i[0], i[-1]
p[0], p[-1]
len(i), len(p)








