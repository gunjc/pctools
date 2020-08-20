"""
Methods for dealing with bucket labels, transforming to dates
and distributing one set of bucket's values to another
"""

# Python
import re
import functools
from itertools import dropwhile

# External
import numpy as np
import pandas as pd

# Project
from pypctools.Calendar import offsetdate


__all__ = ['Label', 'Bucket', 'labeltodate']


@functools.total_ordering
class Label:
    """
    Creation of bucket label objects
    """
    # constants needed for integrity checking
    _single_label_pat = re.compile(r'(\d+)([YMWD])')
    _letter_order_map = {'Y': 0, 'M': 1, 'W': 2, 'D': 3}

    def __new__(cls, *args, **kwargs):
        """
        Implements idempotence. See links for more information:
        https://stackoverflow.com/questions/53481937
        https://www.concentricsky.com/articles/detail/pythons-hidden-new
        """
        # assert we get only the 'label' arg, as in __init__
        if not kwargs and len(args) == 1 and isinstance(args[0], cls):
            return args[0]
        return super(Label, cls).__new__(cls)

    def __init__(self, label):
        # ------ integrity checks -------
        # idempotence: don't need to do __init__ all over again
        if isinstance(label, Label):
            return

        # type check
        if not isinstance(label, str):
            raise TypeError(f'Expected str, got {label.__class__.__name__}')

        # uppercase check
        if not label.isupper():
            raise ValueError(f'Given label "{label}" must be uppercase')

        # splitting label into vertices and consistency checks
        match_list = self._single_label_pat.findall(label)
        if not match_list:
            raise ValueError(f'Invalid label format: {label}')

        # assert all found single labels make the original label string given
        rebuilt_label = ''.join([''.join(tup) for tup in match_list])
        if rebuilt_label != label:
            raise ValueError(f'Invalid label format: {label}')

        # split label's letters and numbers
        numbers = [int(tup[0]) for tup in match_list]
        letters = [tup[1] for tup in match_list]

        # FIXME: assert there are no labels with zero value
        # for no in numbers:
        #     if no == 0:
        #         raise ValueError(f'Zero value in given label: {label}')

        # assert there are no repeated letters
        if max(label.count(char) for char in ''.join(letters)) not in (0, 1):
            raise ValueError(f'Repeated letters in given label: {label}')

        # assert letters are in order Y-M-W-D
        if len(letters) > 1:
            mapped_letters = [self._letter_order_map[c] for c in letters]
            if sorted(mapped_letters) != mapped_letters:
                raise ValueError(f'Label must be in Y-M-W-D order')

        # -------- If we got to here, then it's all good,
        #          now can set the proper attributes --------------

        # map of number of periods for each label
        self._letter_map = {'Y': 0, 'M': 0, 'W': 0, 'D': 0}
        for char, num in zip(letters, numbers):
            self._letter_map[char] = num

        self._label = label
        # day count used only for comparison methods
        self._dc_count = sum(n * self._letter_map.get(c, 0)
                             for n, c in zip((1, 7, 30, 360), 'DWMY'))

    @property
    def label(self):
        return self._label

    @property
    def letter_map(self):
        return self._letter_map

    @property
    def dc_count(self):
        return self._dc_count

    # ----- comparison methods --------
    def __eq__(self, other):
        if not isinstance(other, Label):
            raise TypeError('Label can only be compared with another Label')
        return self._dc_count == other._dc_count

    def __le__(self, other):
        if not isinstance(other, Label):
            raise TypeError('Label can only be compared with another Label')
        return self._dc_count <= other._dc_count
    # ---------------------------------

    def __repr__(self):
        return f'<Label {self.label}>'

    def __str__(self):
        return self.label

    def __hash__(self):
        return hash(repr(self))

    def to_date(self, ref_date, *, date_adjust, cal=None):
        """
        Transforms the Label instance to a date, by shifting the
        given reference date.

        Parameters
        ----------
        ref_date: date_like
            The reference date
        date_adjust: {'DU', 'DC'}
            How to adjust the shifted date. 'DC' means no adjust.
            'DU' adjusts to a business day, according to the given
            `cal` parameter
        cal: str, optional
            The calendar, used when `date_adjust` is 'DU', ignored otherwise

        Returns
        -------
        np.datetime64
            The shifted date
        """
        if not isinstance(date_adjust, str):
            raise TypeError(f'date_adjust parameter must be str, '
                            f'got {date_adjust.__class__.__name__}')
        date_adjust = date_adjust.upper()
        if date_adjust not in {'DU', 'DC'}:
            raise ValueError(f"date_adjust parameter must be "
                             f"'DU' or 'DC', got '{date_adjust}'")

        # it's easier to do date offsets with pandas Timestamp instance
        ref_date = pd.Timestamp(ref_date)
        # number of periods for each label D-W-M-Y
        nd, nw, nm, ny = map(self.letter_map.get, 'DWMY')

        # The label about years is nothing more than the label of months x 12
        nm += 12 * ny
        # The label about weeks is nothing more than the label of days x 7
        nd += 7 * nw

        # So, essentially we are dealing with DAYS and/or MONTHS
        # to shift the date by a label
        shifted = ref_date
        if nm > 0:
            # jump months
            shifted += pd.DateOffset(months=nm)
            if date_adjust == 'DU':
                # Don't move to the next month if in EOM
                shifted = pd.Timestamp(
                    offsetdate(shifted, 0, roll='modifiedfollowing', cal=cal)
                )
        if nd > 0:
            shifted += pd.DateOffset(days=nd)
            if date_adjust == 'DU':
                shifted = offsetdate(shifted, 0, roll='forward', cal=cal)

        return np.datetime64(shifted, 'D')


# Label.to_date v1.1 function
# def to_date(self, ref_date, *, date_adjust, cal=None):
#     """
#     Transforms the Label instance to a date, by shifting the
#     given reference date.
#
#     Parameters
#     ----------
#     ref_date: date_like
#         The reference date
#     date_adjust: {'DU', 'DC'}
#         How to adjust the shifted date. 'DC' means no adjust.
#         'DU' adjusts to a business day, according to the given
#         `cal` parameter
#     cal: str, optional
#         The calendar, used when `date_adjust` is 'DU', ignored otherwise
#
#     Returns
#     -------
#     np.datetime64
#         The shifted date
#     """
#     if not isinstance(date_adjust, str):
#         raise TypeError(f'date_adjust parameter must be str, '
#                         f'got {date_adjust.__class__.__name__}')
#     date_adjust = date_adjust.upper()
#     if date_adjust not in {'DU', 'DC'}:
#         raise ValueError(f"date_adjust parameter must be "
#                          f"'DU' or 'DC', got '{date_adjust}'")
#
#     # it's easier to do date offsets with pandas Timestamp instance
#     ref_date = pd.Timestamp(ref_date)
#     # number of periods for each label D-W-M-Y
#     nd, nw, nm, ny = map(self.letter_map.get, 'DWMY')
#
#     # The label about years is nothing more than the label of months x 12
#     nm += 12 * ny
#     # The label about weeks is nothing more than the label of days x 7
#     nd += 7 * nw
#
#     # So, essentially we are dealing with DAYS and/or MONTHS
#     # to shift the date by a label
#     shifted = ref_date
#     if nm > 0:
#         # jump months
#         shifted += pd.DateOffset(months=nm)
#         if date_adjust == 'DU':
#             # If we are searching for a business day,
#             # go back until one is found
#             shifted = pd.Timestamp(
#                 offsetdate(shifted, 0, roll='modifiedfollowing', cal=cal)
#             )
#     if nd > 0:
#         if date_adjust == 'DC':
#             shifted += pd.DateOffset(days=nd)
#         elif date_adjust == 'DU':
#             if self.letter_map['D'] > 0 and not isbd(shifted, cal=cal):
#                 shifted = offsetdate(shifted, -1, roll='forward', cal=cal)
#             shifted = offsetdate(shifted, nd, roll='forward', cal=cal)
#
#     return np.datetime64(shifted, 'D')


class Bucket(pd.Series):
    """
    A custom pandas Series to represent values allocated in buckets

    Attributes
    ----------
    labels: iterable
        The sequence of labels
    values: iterable, optional
        Values for the given labels. If not given, defaults no NaN

    Methods
    -------
    to_dates(ref_date, *, date_adjust, cal=None)
        Shifts reference date by the Bucket's labels
    distribute_values(verts, *, return_bucket=False)
        Distributes the Bucket's values to another set of labels
    """
    def __init__(self, labels, values=None):
        ix = pd.Index((Label(label) for label in labels), name='Bucket')
        # check there are no duplicated labels
        if not ix.equals(ix.unique()):
            raise ValueError('Given labels must be all unique '
                             '(i.e. different dc_count)')
        pd.Series.__init__(self, index=ix, data=values)
        self.sort_index(inplace=True)

    def to_dates(self, ref_date, *, date_adjust, cal=None):
        """
        Shifts the given reference date by the bucket's labels.

        Parameters
        ----------
        ref_date: date_like
            The reference date
        date_adjust: {'DU', 'DC'}
            How to adjust the shifted date. 'DC' means no adjust.
            'DU' adjusts to a business day, according to the given
            `cal` parameter
        cal: str, optional
            The calendar, used when `date_adjust` is 'DU', ignored otherwise

        Returns
        -------
        np.ndarray
            An array of shifted dates
        """
        return np.array(
            [label.to_date(ref_date, date_adjust=date_adjust, cal=cal)
             for label in self.index]
        )

    def distribute_values(self, verts, *, return_bucket=False):
        """
        Distributes the bucket's values to another set of labels,

        Parameters
        ----------
        verts: list of str or Label
            The sequence of new labels to distribute the values to
        return_bucket: bool, default False
            If False, returns an array of the distributed values,
            else returns a new Bucket instance with the distributed values

        Returns
        -------
        np.ndarray, Bucket
            The bucket's values distributed as an array or as a new
            Bucket instance, according to the `return_bucket` parameter
        """
        if np.any(np.isnan(self.values)):
            raise ValueError("Can't distribute NaN values")

        verts = [Label(label) for label in verts]
        to_ndays = [v.dc_count for v in verts]

        def find_closest(nd):
            # return tuple -> closest label to the right and to the left
            # from: [360, 1080, 2160],
            # to: [720, 1440]
            # find_closest(360) = (None, 720)
            #
            # from: [360, 1080],
            # to: [360, 720]
            # find_closest(360) = (360, 360)
            # find_closest(1080) = (720, None)
            try:
                left = next(dropwhile(
                    lambda to_nd: to_nd > nd, reversed(to_ndays)
                ))
            except StopIteration:
                left = None
            try:
                right = next(dropwhile(
                    lambda to_nd: to_nd < nd, to_ndays
                ))
            except StopIteration:
                right = None

            # left and right cannot be None at the same time
            assert not (left is None and right is None), 'left = right = None!'
            return left, right

        # distribute values in the 'distributed' list
        distributed = [0] * len(verts)
        for label, value in self.iteritems():
            nd_left, nd_right = find_closest(label.dc_count)
            # calculate label's value proportions to the left and right
            if nd_left is None:
                # full value goes to the closest right label
                distributed[to_ndays.index(nd_right)] += value
            elif nd_right is None:
                # full value goes to the closest left label
                distributed[to_ndays.index(nd_left)] += value
            elif nd_left == nd_right:
                # same label, full value goes there
                distributed[to_ndays.index(nd_left)] += value
            else:
                # allocate value proportionally to dc distance
                perc_left = (nd_right - label.dc_count) / (nd_right - nd_left)
                perc_right = (label.dc_count - nd_left) / (nd_right - nd_left)
                # sanity checks
                assert 0 < perc_left < 1
                assert 0 < perc_right < 1
                assert round(perc_left + perc_right, 7) == 1
                distributed[to_ndays.index(nd_left)] += perc_left * value
                distributed[to_ndays.index(nd_right)] += perc_right * value

        # sanity check on the sum of values:
        assert np.isclose(np.sum(distributed), np.sum(self.values), rtol=0, atol=1e-2)

        if return_bucket:
            return Bucket(verts, distributed)
        else:
            return np.array(distributed)


def labeltodate(date, label, *, date_adjust, cal=None):
    """
    Shifts the given date by the given label

    Parameters
    ----------
    date: date_like
        The reference date
    label: str or Label
        The bucket label to shift the date
    date_adjust: {'DU', 'DC'}
        How to adjust the shifted date. 'DC' means no adjust.
        'DU' adjusts to a business day, according to the given
        `cal` parameter
    cal: str, optional
        The calendar, used when `date_adjust` is 'DU', ignored otherwise

    Returns
    -------
    np.datetime64
        The shifted date
    """
    return Label(label).to_date(date, date_adjust=date_adjust, cal=cal)


if __name__ == '__main__':
    lbls = (
        '1M',
        '2M',
        '3M',
        '4M',
        '5M',
        '6M',
    )
    vals = (
        0,
        -186944.77,
        -82848.503,
        -392950.468,
        -129281.249,
        0,
    )
    bkt = Bucket(lbls, vals)
    print(bkt.distribute_values(('1M', '3M', '6M')))
