# -*- coding: utf-8 -*-
"""
@author: Jussi (jnu@iki.fi)
"""

from setuptools import setup, find_packages


setup(
    name='configdot',
    version='0.144',
    description='Config object with attribute access and INI parser',
    author='Jussi Nurminen',
    author_email='jnu@iki.fi',
    license='GPLv3',
    url='https://github.com/NCH-Motion-Laboratory/configdot',
    packages=find_packages(),
    include_package_data=True,
)
