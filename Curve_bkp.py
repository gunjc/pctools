"""
Main functions for dealing with curves and interpolation
"""

# Python
from typing import Iterable

# External
import numpy as np

# Project
from pypctools.Calendar import _calc_term, _normalize_dates, bdbetween
from pypctools.Txts import load_pricing_vertices


__all__ = ['rate2fct', 'fct2rate', 'Curve']


def rate2fct(rates, start_dates, end_dates, *,
             compounding, day_count, cal=None):
    """
    Convert rates to factors

    Parameters
    ----------
    rates: float or array of float
        rate values
    start_dates, end_dates: date_like or array of dates
        The start and end date of the rates
    compounding: {'YIELD', 'LINEAR', 'CONTINUOUS'}
        How interest is accumulated
    day_count: {'BUS/252', 'ACT/360', 'ACT/365', 'ACT/ACT'}
        The day count convention used
    cal: str, optional
        The calendar. Only used when `day_count` is 'BUS/252', ignored
        otherwise

    Returns
    -------
    float or array of float
    """
    if isinstance(rates, Iterable):
        rates = np.fromiter(rates, float)
    term = _calc_term(start_dates, end_dates, day_count=day_count, cal=cal)
    if np.any(term < 0):
        raise ValueError("Unable to calculate factors "
                         "with end_dates < start_dates")

    compounding = compounding.upper()
    if compounding == 'YIELD':
        return (1 + rates) ** term
    elif compounding == 'LINEAR':
        return 1 + rates * term
    elif compounding == 'CONTINUOUS':
        return np.exp(rates * term)
    else:
        raise ValueError(f'Invalid compounding parameter: {compounding}')


def fct2rate(factors, start_dates, end_dates, *,
             compounding, day_count, cal=None):
    """
    Convert factors to rates

    Parameters
    ----------
    factors: float or array of float
        factor values
    start_dates, end_dates: date_like or array of dates
        The start and end date of the factors
    compounding: {'YIELD', 'LINEAR', 'CONTINUOUS'}
        How interest is accumulated
    day_count: {'BUS/252', 'ACT/360', 'ACT/365', 'ACT/ACT'}
        The day count convention used
    cal: str, optional
        The calendar. Only used when `day_count` is 'BUS/252', ignored
        otherwise

    Returns
    -------
    float or array of float
    """
    if isinstance(factors, Iterable):
        factors = np.fromiter(factors, float)
    term = _calc_term(start_dates, end_dates, day_count=day_count, cal=cal)
    if np.any(term < 0):
        raise ValueError("Unable to calculate factors "
                         "with end_dates < start_dates")

    compounding = compounding.upper()
    if compounding == 'YIELD':
        return factors ** (1 / term) - 1
    elif compounding == 'LINEAR':
        return (factors - 1) / term
    elif compounding == 'CONTINUOUS':
        return np.log(factors) / term
    else:
        raise ValueError(f'Invalid compounding parameter: {compounding}')


class Curve:
    def __init__(self, start_dates, end_dates, rates, *,
                 interp_method, compounding, day_count, cal):
        start_dates = _normalize_dates(start_dates)
        end_dates = _normalize_dates(end_dates)

        # ------- consistency checks -----------------
        if not isinstance(rates, Iterable):
            raise TypeError("'rates' parameter must be array_like")
        rates = np.fromiter(rates, float)

        # length-consistency checks on dates and rates
        if isinstance(end_dates, np.ndarray):
            if not isinstance(start_dates, np.ndarray):
                # single start_date given, create array:
                start_dates = np.repeat(start_dates, len(end_dates))
            if len(start_dates) != len(end_dates):
                raise ValueError('start and end dates must '
                                 'have the same length')
            if len(end_dates) != len(rates):
                raise ValueError('end_dates and rates must '
                                 'have the same length')
        else:
            raise ValueError('end_dates must be array_like')

        # other checks on end_dates
        if not np.array_equal(np.sort(end_dates), end_dates):
            raise ValueError('end_dates must be sorted in ascending order')
        if not len(np.unique(end_dates)) == len(end_dates):
            raise ValueError('end_dates must be all unique')

        # curve reference date, implied by 'start_dates':
        ref_date = start_dates[0]

        # busday count consistency check:
        if day_count.upper() == 'BUS/252':
            nbusdays = bdbetween(ref_date, end_dates, cal=cal)
            if len(np.unique(nbusdays)) != len(nbusdays):
                raise ValueError('Dates given must have no repeated '
                                 'business days count')

        if interp_method.upper() not in {'LIN', 'EXP'}:
            raise ValueError(f"interp_method parameter must be 'LIN' or 'EXP'")

        # --- determination of ZC factors for the curve ---
        factors = []
        for i in range(len(end_dates)):
            temp_fct = rate2fct(rates[i], start_dates[i], end_dates[i],
                                compounding=compounding, day_count=day_count,
                                cal=cal)
            if start_dates[i] == ref_date:
                # already a ZC factor, nothing to do
                pass
            else:
                # find the FRA from previous factors:
                found_fra = False
                for j in range(i):
                    if end_dates[j] == start_dates[i]:
                        # now we can determine the ZC factor:
                        found_fra = True
                        temp_fct *= factors[j]
                if not found_fra:
                    raise ValueError("Cannot calculate FRA's with given dates")

            factors.append(temp_fct)
        factors = np.array(factors)

        # ---- done with checks, now we can set the curve's attributes ----
        self.ref_date = ref_date
        self.start_dates = start_dates
        self.end_dates = end_dates
        self.interp_method = interp_method.upper()
        self.compounding = compounding.upper()
        self.day_count = day_count.upper()
        self.factors = factors
        self.rates = fct2rate(factors, ref_date, end_dates,
                              compounding=compounding, day_count=day_count,
                              cal=cal)
        if interp_method.upper() == 'EXP':
            self.log_factors = np.log(factors)  # for exponential interpolation
        else:
            self.log_factors = None
        # ndays: the x axis for interpolation:
        if day_count.upper() == 'BUS/252':
            self.cal = cal.upper()
            self.ndays = bdbetween(ref_date, end_dates, cal=cal)
        else:
            self.cal = None
            self.ndays = (end_dates - ref_date).astype(int)

    def __zc_r2f(self, rates, dates):
        """
        Wrapper around rate2fct, customized for this Curve instance.
        Calculates factors from Curve's ref_date to given dates.
        """
        return rate2fct(rates, self.ref_date, dates,
                        compounding=self.compounding, day_count=self.day_count,
                        cal=self.cal)

    def __zc_f2r(self, factors, dates):
        """
        Wrapper around fct2rate, customized for this Curve instance.
        Calculates rates from Curve's ref_date to given dates.
        """
        return fct2rate(factors, self.ref_date, dates,
                        compounding=self.compounding, day_count=self.day_count,
                        cal=self.cal)

    def interp(self, dates):
        """
        Interpolate the curve in the given dates. The rates returned
        are ZC rates, i.e. from the curve's reference date to the `dates`.

        Parameters
        ----------
        dates: date_like or array of dates
            Dates to interpolate

        Returns
        -------
        float or array of float
            Interpolated rates
        """
        dates = _normalize_dates(dates)

        # calculate the ndays from curve's ref_date
        if self.day_count == 'BUS/252':
            x = bdbetween(self.ref_date, dates, cal=self.cal)
        else:
            x = (dates - self.ref_date).astype(int)

        if self.interp_method == 'EXP':
            # little hack: when the given date is outside the Curve's
            # date range, force it temporarily to one of the boundaries,
            # so exponential interpolation will return flat rates
            # automatically by np.interp and fct2rate
            if isinstance(dates, np.ndarray):
                dates = np.where(dates < self.end_dates[0],
                                 self.end_dates[0], dates)
                dates = np.where(dates > self.end_dates[-1],
                                 self.end_dates[-1], dates)
            else:
                dates = max(min(dates, self.end_dates[-1]), self.end_dates[0])

            # linear interpolation on the log of Curve's factors:
            interp_factors = np.exp(np.interp(x, self.ndays, self.log_factors))
            # return rates:
            return self.__zc_f2r(interp_factors, dates)
        elif self.interp_method == 'LIN':
            # linear interpolation on rates
            return np.interp(x, self.ndays, self.rates)

    def fra_interp(self, start_dates, end_dates):
        """
        Curve interpolation to return a forward rate

        Parameters
        ----------
        start_dates, end_dates: date_like or array of dates
            The start and end dates for the FRA

        Returns
        -------
        float or array of float
            Interpolated rates
        """
        start_factors = self.__zc_r2f(self.interp(start_dates), start_dates)
        end_factors = self.__zc_r2f(self.interp(end_dates), end_dates)
        return fct2rate(end_factors / start_factors, start_dates, end_dates,
                        compounding=self.compounding, day_count=self.day_count,
                        cal=self.cal)

    def __repr__(self):
        return f'Curve: ref_date = {self.ref_date}, ' \
               f'with {len(self.end_dates)} points.'

    @classmethod
    def from_vertices_txt(cls, curve_name: str, ref_date, **curve_kwargs):
        """
        Instantiate a Curve directly from a Pricing vertices txt

        Parameters
        ----------
        curve_name: str
            The base filename of the curve
        ref_date: date_like
            The reference date
        curve_kwargs:
            Curve's keyword arguments: interp_method, compounding, day_count
            and cal

        Returns
        -------
        Curve
        """
        df = load_pricing_vertices(curve_name, ref_date)
        return cls(
            df['START_DATE'], df['END_DATE'], df['RATE'], **curve_kwargs
        )


if __name__ == '__main__':
    # read ON_BRL vertices txt from 2019-07-31
    cparams = dict(interp_method='EXP', compounding='YIELD', day_count='BUS/252', cal='BRL')
    fparams = dict(compounding='YIELD', day_count='BUS/252', cal='BRL')

