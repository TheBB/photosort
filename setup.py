#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='Photosort',
    version='0.1',
    description='Photo organizing tool',
    author='Eivind Fonn',
    author_email='evfonn@gmail.com',
    license='GPL3',
    url='https://github.com/TheBB/photosort',
    py_modules=['photosort'],
    entry_points={
        'console_scripts': ['photosort=photosort.__main__:main'],
    },
    install_requires=[
        'click',
        'memoized_property',
        'py3exiv2',
        'pyqt5',
        'tqdm',
    ],
)
