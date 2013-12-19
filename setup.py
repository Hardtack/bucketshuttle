from __future__ import with_statement

import os.path

try:
    from setuptools import setup
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

from bucketshuttle.version import VERSION


def readme():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
            return f.read()
    except IOError:
        pass


with open('requirements.txt') as f:
    requirements = list(line.strip() for line in f)


setup(
    name='bucketshuttle',
    packages=['bucketshuttle'],
    package_data={
        'bucketshuttle': ['templates/*.*'],
        '': ['README.rst', 'requirements.txt', 'distribute_setup.py']
    },
    version=VERSION,
    description='Static HTML server with bitbucket authorization',
    long_description=readme(),
    license='MIT License',
    author='GunWoo Choi',
    author_email='6566gun' '@' 'gmail.com',
    maintainer='GunWoo Choi',
    maintainer_email='6566gun' '@' 'gmail.com',
    url='https://github.com/hardtack/bucketshuttle',
    install_requires=requirements,
    entry_points = {
        'console_scripts': [
            'bucketshuttle = bucketshuttle.run:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Documentation',
        'Topic :: Software Development :: Documentation'
    ]
)
