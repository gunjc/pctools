"""
DATAMART DIRECT LOAD FROM MOBKP
"""

# Python
import os
import zipfile
import ftplib
import fnmatch

# External
import pandas as pd
import numpy as np

# Project
from .utils import dead_filter, portfolio_filter, expired_filter


__all__ = ['Datamart', 'BondViews', 'load']


# ------- Main Class -----------------------------------

class Datamart:
    root_folder = r'\\bsbrsp369\Mobkp\DATABASE\DATAMART\CSV'

    def __init__(self):
        self._file_types_cache = None

        # define folder to save the datamart files
        # to TEMP/Datamart (default), if needed
        usr_temp_folder = os.environ.get('TEMP')
        if usr_temp_folder is not None:
            self.ftp_folder = os.path.join(usr_temp_folder, 'Datamart')
        else:
            self.ftp_folder = None

    def ftp_download(self, pattern):
        """
        Download datamart file(s) directly from FTP and save locally

        Parameters
        ----------
        pattern: str
            The pattern string. See
            https://docs.python.org/3/library/fnmatch.html
        """
        if self.ftp_folder is None:
            raise OSError('TEMP environment variable not found')
        if not os.path.isdir(self.ftp_folder):
            os.mkdir(self.ftp_folder)

        with ftplib.FTP(host='SIBRPROD', user='ftpmxmd', passwd='ftpmxmd') as ftp:
            # diretório Datamart
            ftp.cwd('/sistemas/home/plbrasil/DATAMART_MX3')

            # find files to download based on pattern given
            files = fnmatch.filter(ftp.nlst(), pattern)
            if not files:
                raise FileNotFoundError(f'Found no files in datamart matching pattern "{pattern}"')

            # download requested files (takes a while for each one...)
            for file in files:
                to_filepath = os.path.join(self.ftp_folder, file)
                if not os.path.isfile(to_filepath):
                    with open(to_filepath, 'wb') as f:
                        print(f'Downloading {file}')
                        ftp.retrbinary(f'RETR {file}', f.write)
                else:
                    print(f'Skipped {file}, already in {self.ftp_folder}')

    @staticmethod
    def _clean_frame(df) -> None:
        """
        Strips whitespace from strings, an annoying behaviour
        in the datamart files.
        """
        # this may include python objects, other than str (what we want),
        # but it probably won't happen
        obj_cols = df.select_dtypes(np.object_).columns
        if not obj_cols.empty:
            df[obj_cols] = df[obj_cols].apply(lambda s: s.str.strip())
            print(f'Stripped {len(obj_cols)} cols')

        # Parse dates:
        default_date_fmt = "%d/%m/%Y"
        # a list containing sequences of (date column, its date format)
        date_cols = [
            ('TRNDATE', default_date_fmt),
            ('MSYSDATE', default_date_fmt),
            ('DATEPERIODEXPIRYDATE', default_date_fmt),
            ('DATEPERIODCALCEND', default_date_fmt),
            ('DATEPERIODSTARDATE', default_date_fmt),
            ('DATELASTFIXING', default_date_fmt),
            ('LASTMARKETOPERATIONDATE', default_date_fmt),
            ('MARKETOPERATIONFIRSTDATE', default_date_fmt),
            ('START_DATE', None),
        ]
        for date_col, fmt in date_cols:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], format=fmt)

    def load(self, which: str, ref_date, *, cleanup=True) -> pd.DataFrame:
        """
        Load a datamart csv file from MOBKP network dir

        :param which: str
            The root file name, e.g. 'MOPL_BR_BO', 'MOPL_BR_FU'
        :param ref_date: str or datetime-like
            The reference date
        :param cleanup: bool
            Apply str.strip to columns with str dtype
        :return: pandas.DataFrame
            The csv file in a dataframe
        """
        which = which.upper()
        ref_date_str = pd.Timestamp(ref_date).strftime("%Y%m%d")
        csv_fname = f'{which}_{ref_date_str}.csv'

        def find_file():
            """Tries to find the goddamn datamart file somewhere"""
            # csv lookup:
            csv_fpath = os.path.join(self.root_folder, csv_fname)
            if os.path.isfile(csv_fpath):
                print('Located csv')
                return csv_fpath
            zip_fpath = os.path.join(self.root_folder, f'{which}_{ref_date_str}.zip')
            if os.path.isfile(zip_fpath):
                print('Located zip')
                with zipfile.ZipFile(zip_fpath) as zipf:
                    return zipf.open(csv_fname)
            local_fpath = os.path.join(self.ftp_folder, csv_fname)
            if os.path.isfile(local_fpath):
                print('Located in TEMP')
                return local_fpath
            else:
                # last resource: donwload from FTP
                print('Searching in FTP...')
                self.ftp_download(csv_fname)
                return local_fpath

        read_csv_kwargs = dict(sep=';', error_bad_lines=False)

        df = pd.read_csv(find_file(), **read_csv_kwargs)

        if cleanup:
            self._clean_frame(df)

        return df

    @property
    def file_types(self):
        """
        Returns a set of different available datamart filenames
        that can be used in the ``which`` parameter in the load
        method.
        """
        # we cache the available file types because searching
        # the entire directory takes a bit of time
        if self._file_types_cache is None:
            self._file_types_cache = set(
                f.name.rsplit('_', 1)[0]
                for f in os.scandir(self.root_folder)
                if f.name.endswith('.zip')
            )
            print(f'{self.root_folder} scanned')
        return self._file_types_cache


# ------- Convenience API ------------------------------

_DM = Datamart()  # Datamart instance for internal use


def load(which, ref_date, *, cleanup=True):
    return _DM.load(which, ref_date, cleanup=cleanup)


# ------------ development ------------


class BondViews:
    """Quick bond routine data grouping"""
    def __init__(self, ref_date):
        self.ref_date = pd.Timestamp(ref_date)
        self.df = load('MOPL_BR_BO', ref_date)

    def _filter_and_sort(self, portfolios) -> pd.Series:
        s = self.df.pipe(dead_filter) \
                   .pipe(portfolio_filter, portfolios) \
                   .pipe(expired_filter, self.ref_date) \
                   .groupby('INSTRUMENT')['LIVEQUANTITY'].sum()
        return s.loc[s != 0].sort_values(ascending=False)

    def debs_mm(self):
        """
        Retorna série indexada por papel, com a quantidade líquida de cada
        da carteira de Market Making, em ordem decrescente.
        """
        portfolios = ['BAL_DEBEN_BSB', 'BAL_DEBCLI_BSB', 'BAL_DEBPASS_BSB',
                      'BAL_DEBENSR_BSB']
        return self._filter_and_sort(portfolios)

    def debs_hermes(self):
        portfolios = ['RA_HERMES', 'RA_HERMES_MARCO']
        return self._filter_and_sort(portfolios)

    def debs_sobras_emissao_primaria(self):
        portfolios = ['BAL_DEBFSA_BSB']
        return self._filter_and_sort(portfolios)

    def hedge_ntnbs(self):
        """Portfolio com as NTN-B's de hedge de debêntures"""
        portfolios = ['BAL_DEBP_RF_BSB']
        return self._filter_and_sort(portfolios)


class EqViews:
    """Equity analytics"""
    def __init__(self, ref_date):
        self.ref_date = pd.Timestamp(ref_date)
        self.df = load('MOPL_BR_EQ', ref_date)

    def position(self):
        pdf = dead_filter(self.df)
        pdf = pdf.loc[pdf['CONTRACTTYPOLOGY'] == 'Equity']
        s = pdf.groupby(['INSTRUMENT'])['LIVEQUANTITY'].sum()

        return s.loc[s != 0].sort_values(ascending=False)


def inst_roll(df, inst):
    # test
    """Acumulado da posição de um instrumeto específico ao longo do tempo"""
    inst_df = df.loc[df['INSTRUMENT'] == inst]
    inst_df = inst_df.loc[inst_df['STATUSLIVEMKT_OPDEAD'] != 'DEAD']
    return inst_df.groupby(['TRNDATE'])['LIVEQUANTITY'].sum().cumsum()

























