"""
Essential functions for dealing with business days dates
"""

# Python
import datetime as dt
import pkgutil
import collections
from typing import Iterable
from xml.etree import ElementTree

# External
import numpy as np
import pandas as pd


__all__ = ['isbd', 'bdbetween', 'offsetdate', 'bday_range']


# dict of holidays, in the form {country: np.busdaycalendar}
# to be cached and loaded on demand
_CALENDARS = dict()


# ------------------ private methods --------------------


def _xldate_to_datetime(xldate):
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


def _load_calendar(cal):
    """
    If the calendar given is not already loaded, finds the appropriate xml
    file with the holidays list, and caches it in the global _CALENDARS dict
    as a numpy.busdaycalendar object.
    This function should only be called by the _get_calendar function.

    Parameters
    ----------
    cal: str
        Input calendar
    """
    # check if calendar given is not already cached
    if cal in _CALENDARS:
        return

    try:
        # loading package static data: see Python Cookbook 3rd ed. recipe 10.8
        data = pkgutil.get_data(__package__, f'./Calendars/{cal}.xml')
        # # Testing line for console cooking. Uncomment, call function, and recomment it right after # #
        # data = open(fr'pypctools\Calendars\{cal}.xml').read()
    except FileNotFoundError:
        raise ValueError(f'Invalid/NotImplemented calendar: {cal}')

    root = ElementTree.fromstring(data)
    holidays = np.array([_xldate_to_datetime(int(child.text))
                         for child in root], dtype='datetime64[D]')
    _CALENDARS[cal] = np.busdaycalendar(holidays=holidays)


def _get_bdaycalendar(cal):
    """
    Gets the appropriate np.busdaycalendar for the given country's
    calendar, or a cross-calendar if more than one was given.

    Parameters
    ----------
    cal: str
        The calendar(s)

    Returns
    -------
    np.busdaycalendar
        The businessday calendar (or cross-calendar)
        with the appropriate holidays
    """
    if not isinstance(cal, str):
        raise TypeError(f'Calendar input must be str, '
                        f'got {cal.__class__.__name__}')
    cals = cal.upper().split()
    # load given calendar(s), if not already loaded:
    for cal in cals:
        _load_calendar(cal)

    if len(cals) == 1:
        return _CALENDARS[cals[0]]
    elif len(cals) > 1:
        # cross calendar required: join the required calendars' holidays
        # and return a new np.busdaycalendar with the merged holidays
        cross_cal = np.busdaycalendar(
            holidays=np.concatenate([_CALENDARS[cal].holidays for cal in cals])
        )
        return cross_cal
    else:
        # we should never get here, but who knows...
        raise RuntimeError(f'Unexpected calendar: {cal}')


def _normalize_dates(dates):
    """
    Convenience function to transform a date to np.datetime64[D],
    since all of numpy busday functions require this data type.
    We transform a given input date to a pandas Timestamp, and then
    to np.datetime64[D]. This way we get the flexibility of different
    ways for date input to use in busday functions defined in this module.

    Parameters
    ----------
    dates: str, dt.datetime or array_like of dates
        A date or sequence of dates, in any format that can be converted
        to a pandas Timestamp.

    Returns
    -------
        The same input but with dates transformed to np.datetime64[D] dtype.

    """
    # transform given dates to the very flexible
    # pandas.Timestamp, and then to np.datetime64
    if isinstance(dates, Iterable) and not isinstance(dates, str):
        return np.array([np.datetime64(pd.Timestamp(v), 'D') for v in dates])
    else:
        # single input case
        return np.datetime64(pd.Timestamp(dates), 'D')


def _calc_term(start_dates, end_dates, *, day_count, cal=None):
    if not isinstance(day_count, str):
        raise TypeError(f'day_count parameter must be str, '
                        f'got {day_count.__class__.__name__}')
    day_count = day_count.upper()
    _available_day_counts = {'BUS/252', 'ACT/360', 'ACT/365', 'ACT/ACT'}
    if day_count not in _available_day_counts:
        raise ValueError(f'day_count given must '
                         f'be one of {_available_day_counts}')

    if day_count == 'BUS/252':
        return bdbetween(start_dates, end_dates, cal=cal) / 252

    # other day counts: need to normalize dates
    start_dates = _normalize_dates(start_dates)
    end_dates = _normalize_dates(end_dates)

    def act_act_term(start, end):
        """
        Calculation of ACT/ACT term: equals
            (days_not_in_leap_year / 365) + (days_in_leap_year / 366)
        Parameters (start, end) should be scalars.
        """
        start, end = map(pd.Timestamp, (start, end))
        sign = 1
        # in case the start date is greater than the end date,
        # we swap the dates, do the calculations normally, and
        # just multiply the result term by -1.
        if start > end:
            sign = -1
            start, end = end, start

        term = 0
        for year in range(start.year, end.year + 1):
            den = 366 if pd.Timestamp(str(year)).is_leap_year else 365

            if year == start.year == end.year:
                num = (end - start).days
            elif year == start.year:
                num = (pd.Timestamp(str(year + 1)) - start).days
            elif year == end.year:
                num = (end - pd.Timestamp(str(year))).days
            else:
                # start.year < year < end.year
                num = (pd.Timestamp(str(year + 1))
                       - pd.Timestamp(str(year))).days

            term += num / den

        return term * sign

    if day_count == 'ACT/ACT':
        return_scalar = False  # flag to return a scalar or np.array
        if isinstance(end_dates, np.ndarray):
            if not isinstance(start_dates, np.ndarray):
                start_dates = np.repeat(start_dates, len(end_dates))
            if len(start_dates) != len(end_dates):
                raise ValueError('start and end dates must '
                                 'have the same length')
        else:
            start_dates = np.array([start_dates])
            end_dates = np.array([end_dates])
            return_scalar = True

        result = np.array([act_act_term(s, e) for (s, e)
                           in zip(start_dates, end_dates)])

        if return_scalar:
            return result[0]
        else:
            return result

    actual_count = (end_dates - start_dates).astype(int)
    if day_count == 'ACT/365':
        return actual_count / 365
    if day_count == 'ACT/360':
        return actual_count / 360

    raise ValueError(f'Invalid day_count: {day_count}')


# ------------------ public API -----------------------


def isbd(dates, *, cal='BRL'):
    """
    Calculates which of the given dates are valid business days,
    according to the given calendar(s).

    Parameters
    ----------
    dates: date_like or array of dates
        Input dates to check
    cal: str
        Calendar(s). Default is 'BRL'

    Returns
    -------
    bool or array of bool
        A bool or array of bool, with the same shape as ``dates``,
        containing False if the date falls on a weekend or holiday
        and True otherwise.
    """
    bdaycal = _get_bdaycalendar(cal)
    dates = _normalize_dates(dates)
    return np.is_busday(dates, busdaycal=bdaycal)


def bdbetween(start_dates, end_dates, *, cal='BRL'):
    """
    Counts the number of business days between `start_dates` and
    `end_dates`, not including the day of `end_dates`, according
    to the given calendar(s).

    If `end_dates` specifies a date value that is earlier than the
    corresponding `start_dates` date value, the count will be negative.

    Parameters
    ----------
    start_dates: date_like or array of dates
        The start dates
    end_dates: date_like or array of dates
        The end dates
    cal: str
        Calendar(s). Default is 'BRL'

    Returns
    -------
    int or array of int
        The number of business days between given period. The return
        array will be of the same shape as ``end_dates`` array.
    """
    bdaycal = _get_bdaycalendar(cal)
    start_dates = _normalize_dates(start_dates)
    end_dates = _normalize_dates(end_dates)
    return np.busday_count(start_dates, end_dates, busdaycal=bdaycal)


def offsetdate(dates, offsets, *, roll='forward', cal='BRL'):
    """
    First adjusts the date to fall on a valid day according to the `roll` rule,
    then applies offsets to the given dates counted in valid days, according
    to the given calendar

    Parameters
    ----------
    dates: date_like or array of dates
        The array of dates to process.
    offsets: int or array of int
        The array of offsets, which is broadcast with `dates`.
    roll : {'raise', 'nat', 'forward', 'following', 'backward', 'preceding',
            'modifiedfollowing', 'modifiedpreceding'}, optional
        How to treat dates that do not fall on a valid day. The default
        is 'forward'.

          * 'raise' means to raise an exception for an invalid day;
          * 'nat' means to return a NaT (not-a-time) for an invalid day;
          * 'forward' and 'following' mean to take the first valid day
            later in time;
          * 'backward' and 'preceding' mean to take the first valid day
            earlier in time;
          * 'modifiedfollowing' means to take the first valid day
            later in time unless it is across a Month boundary, in which
            case to take the first valid day earlier in time;
          * 'modifiedpreceding' means to take the first valid day
            earlier in time unless it is across a Month boundary, in which
            case to take the first valid day later in time.
    cal : str
        The calendar, default 'BRL'

    Returns
    -------
    np.datetime64[D] or array of np.datetime64[D]
        An array with a shape from broadcasting `dates` and `offsets`
        together, containing the dates with offsets applied.
    """
    bdaycal = _get_bdaycalendar(cal)
    dates = _normalize_dates(dates)
    return np.busday_offset(
        dates, offsets, roll=roll.lower(), busdaycal=bdaycal
    )


def bday_range(start=None, end=None, periods=None, cal='BRL'):
    """
    Generates a sequence of business days. Includes `start` (if it's a business
    day) and/or includes `end` (if it's a business day)

    Parameters
    ----------
    start: date_like
        The start date
    end: date_like
        The end date
    periods: int
        The number of days to generate
    cal: str
        The calendar. Default 'BRL'

    Returns
    -------
    pd.DatetimeIndex

    Notes
    -----
    Of the three parameters (start, end, periods), exactly two must be specified
    """
    if collections.Counter((start, end, periods)).get(None) != 1:
        raise ValueError("Of the three parameters (start, end, periods), "
                         "exactly two must be specified")
    return pd.bdate_range(start, end, periods, freq='C',
                          holidays=_get_bdaycalendar(cal).holidays)
