# coding: utf8
from setuptools import setup, find_packages


__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


setup(name='unklearn_python_runtime',
      version='0.1',
      description='Python runtime for Unklearn notebooks',
      author='Tharun Mathew Paul',
      author_email='tmpaul06@gmail.com',
      license='MIT',
      packages=find_packages('.', include=['core'], exclude=['**/tests/*.py']),
      zip_safe=True,
      project_urls={
        "Source Code": "https://github.com/unklearn/python-runtime",
      },
      extras_require={
        'testing': [
            'pytest==4.6.1',
            'coverage==4.5.3'
        ]
      },
      install_requires=[
            'tornado==5.0.0',
            'requests==2.22.0',
            'flask-socketio==3.3.2'
      ])

