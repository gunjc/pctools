
from setuptools import setup
import re

# _version added thanks to pdblp's package
# https://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package#7071358
VERSIONFILE = f"pypctools/_version.py"
with open(VERSIONFILE, "rt") as f:
    verstrline = f.read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    version_str = mo.group(1)
else:
    raise RuntimeError(f"Unable to find version string in {VERSIONFILE}")


setup(
    name='pypctools',
    version=version_str,
    packages=['pypctools'],
    include_package_data=True,
    url='',
    license='',
    author='Santander',
    author_email='cjung@santander.com.br',
    description='Extended PCTOOLS excel add-in for Python',
    classifiers=['Programming Language :: Python :: 3'],
    python_requires='>=3',
    install_requires=['numpy', 'pandas'],
)
