"""
Muitos processos necessitam de histórico diário de dados. Guardá-los em um arquivo CSV
é muito prático, porém deve se atentar a não repetir dados e não perder tempo colocando
dados que já estão lá. Por isso foi criado a classe 'CSVDataAppender'.
"""

import os
from typing import Callable
import pandas as pd


class CSVDataAppender:
    """
    Useful class for appending data to CSV's

    Easy append data on csv files.
    CSV must be ';' separated; First column must be a date in "%Y-%m-%d" format;
    Header must be one-line; and the first header column must be named 'DATE'.

    Feature: checks dates integrity, making sure there are no duplicates
    """
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.df = pd.read_csv(filepath, sep=';', header=0, parse_dates=[0], index_col=0,
                              date_parser=lambda v: pd.to_datetime(v, format="%Y-%m-%d"))
        self.csv_modified = False  # signal to save the csv only if it has been modified

    def append_row(self, date, func: Callable):
        """
        Will only append a row if the date is not in the CSV. Therefore, the ``func`` function won't
        be called if ``date`` is already in CSV, thus not wasting everybody's time.
        :param date: reference date
        :param func: function to get the row values, given the date, i.e. row_values = func(date)
        """
        pd_date = pd.Timestamp(date)
        if date in self.df.index:
            print(f'CSVAppender skipping date {pd_date.strftime("%Y-%m-%d")} for file {self.filename}')
        else:
            row_values = func(date)
            self.df.loc[pd_date] = row_values
            self.csv_modified = True

    def commit(self):
        """Saves the appended csv, overwriting the file. Keeps date index in ascending order"""
        if self.csv_modified:
            self.df.sort_index(ascending=True).to_csv(self.filepath, sep=';', index=True, header=True)
            self.csv_modified = False  # resets csv_modified state

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # only commits if there was no exception in the 'with' block
            self.commit()
        else:
            print(f'Exception occurred, CSV {self.filename} not saved.')
