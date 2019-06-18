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
            'pytest',
            'coverage',
            'pytest-mock',
            'pytest-asyncio'
        ],
        'development': [
            'yapf'
        ]
      },
      classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
      ],
      install_requires=[
            'tornado',
            'requests',
            'flask-socketio'
      ])

