
from setuptools import find_packages, setup

setup(
    name='authoritah',
    version=open('VERSION').read(),
    description='Lightweight, agnostic RBAC authorization library',
    author='Shahar Evron',
    author_email='shahar@shoppimon.com',
    url='https://github.com/shoppimon/authoritah',
    packages=find_packages(),
    install_requires=['six'],
    tests_require=['pytest']
)
