'''
Copyright 2022 Airbus SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
# coding: utf-8

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='sos-trades-api',
    version='0.1.0',
    description='API of System of System Trades',
    long_description=readme,
    author='Airbus SAS',
    url='https://idas661.eu.airbus.corp/sostrades/sostrades_webapi.git',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    include_package_data=True,
    python_requires='>=3.7',
    install_requires=[
        'nose2==0.9.1',
        'python-dotenv==0.12.0',
        'SQLAlchemy==1.3.13',
        'Flask==1.1.1',
        'Flask-SQLAlchemy==2.4.1',
        'Flask-Migrate==2.5.2',
        'Flask-Cors==3.0.8',
        'itsdangerous==1.1.0',
        'passlib==1.7.2',
        'flask-jwt-extended==3.24.1',
        'flask_login==0.5.0',
        'mysqlclient==1.4.6',
        'kubernetes==11.0.0',
        'flask-socketio==4.3.0',
        'eventlet==0.25.2',
        'requests-toolbelt==0.9.1',
        'python-ldap==3.3.0',
        'python3-saml==1.9.0',
        'plotly==5.3.0',
        'PyJWT==1.7.1',
        'python-socketio==4.5.1',
        'python-engineio==3.12.1',
        'psutil==5.6.3',
        'graphviz',
        'pycryptodome==3.9.8',
        'pandas==1.3.0'
    ]
)
