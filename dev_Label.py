"""
Try to implement pct.Label as a subclass of str,
so operations will be more convenient.
"""

import re
import functools
from weakref import WeakValueDictionary

import numpy as np
import pandas as pd
from pypctools.Calendar import offsetdate


class NewLabel(str):
    """
    Creation of bucket label objects
    """
    __cache = WeakValueDictionary()

    # constants needed for integrity checking
    _single_label_pat = re.compile(r'(\d+)([YMWD])')
    _letter_order_map = {'Y': 0, 'M': 1, 'W': 2, 'D': 3}

    def __new__(cls, label):
        """
        Implements caching and idempotence. See links for more information:
        https://stackoverflow.com/questions/16977196/how-to-make-two-objects-have-the-same-id-in-python
        https://stackoverflow.com/questions/53481937/python-creating-an-idempotent-initializer
        https://www.concentricsky.com/articles/detail/pythons-hidden-new
        """
        print('__new__')
        if isinstance(label, cls):
            print(f'Same class, returned new')
            return label

        if label in cls.__cache:
            print(f'{label} returned from cache')
            return cls.__cache[label]

        # cache newly created object
        cls.__cache[label] = label_obj = str.__new__(cls, label)
        return label_obj

    def __init__(self, label):
        print(f'__init__ received {label} of type {type(label)}')
        # idempotence: don't need to do __init__ all over again
        if isinstance(label, type(self)):
            print('skipped __init__')
            return

        # ------ integrity checks -------
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
        self.letter_map = {'Y': 0, 'M': 0, 'W': 0, 'D': 0}
        for char, num in zip(letters, numbers):
            self.letter_map[char] = num

        # day count used only for comparison methods
        self.dc_count = sum(n * self.letter_map.get(c, 0)
                            for n, c in zip((1, 7, 30, 360), 'DWMY'))
        str.__init__(label)
        print('__init__ finished')
        # update cache with label's added attributes:
        self.__cache[label] = self

    def __repr__(self):
        return f'<Label {self}>'

    # ----- comparison methods, override every str cmp method --------
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.dc_count == other.dc_count
        if isinstance(other, str):
            return self.dc_count == type(self)(other).dc_count
        raise TypeError('Label can only be compared with another Label')

    def __le__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError('Label can only be compared with another Label')
        return self.dc_count <= other.dc_count
    # ---------------------------------


def label_tests():
    v1 = NewLabel('1M')
    v2 = NewLabel('3M')
    NewLabel(v1)
    assert v2 > v1
    assert v1 > '1D'
    assert v2 > '11M'
    assert v2 > '11M'
















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

