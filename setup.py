from setuptools import setup

def _get_requires():
    with open('requirements.txt') as f:
        return [p.rstrip() for p in f.readlines()]


setup(
    name='anapyzer',
    version='0.0.2',
    url='https://github.com/pbandj082/anapyzer',
    packages=['anapyzer'],
    requires=_get_requires(),
    extras_requires={
        'dev': ['pytest']
    },
)