from setuptools import setup, find_packages

setup(
    name='purreader',
    version='0.1',
    packages=find_packages(),
    install_requires=['pyserial>=3.0']
)