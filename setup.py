import warnings

from setuptools import setup, find_packages

install_requires = [
    'stringcase >=1.2.0',
    'deepdiff >=3.3.0',
    'attrs >=17.2.0',
]


def read_version(version_module_file='openapilib/version.py'):
    context = {}
    with open(version_module_file) as fp:
        exec(fp.read(), context)

    return context['__version__']


def read_long_description(rst_file='README.rst'):
    try:
        with open(rst_file) as fd:
            return fd.read()
    except IOError:
        warnings.warn(f'Could not read long description from {rst_file}')


version = read_version()

setup(
    name='openapilib',
    author='Joar Wandborg',
    author_email='joar+pypi@wandborg.se',
    url='https://github.com/joar/py-openapilib',
    packages=find_packages(),
    description='OpenAPI 3 object model library',
    long_description=read_long_description(),
    install_requires=install_requires,
)
