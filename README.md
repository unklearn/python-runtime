# python-runtime

### Build status
[![Build Status](https://travis-ci.org/unklearn/python-runtime.svg?branch=master)](https://travis-ci.org/unklearn/python-runtime)

### Code climate
<a href="https://codeclimate.com/github/unklearn/python-runtime/maintainability"><img src="https://api.codeclimate.com/v1/badges/f1ec5e92222eb0ebd930/maintainability" /></a>
<a href="https://codeclimate.com/github/unklearn/python-runtime/test_coverage"><img src="https://api.codeclimate.com/v1/badges/f1ec5e92222eb0ebd930/test_coverage" /></a>

A runtime for unklearn notebooks to run python code


### Running test locally

To run local tests, first create a virtual environment with python3.

```bash
    virtualenv venv -p python3
    
    source venv/bin/activate
    
    pip install ".[testing]"
    
    pytest
```

### File formatting

This repo uses [yapf](https://github.com/google/yapf) to format the files. Install yapf using.

```bash

    pip install ".[development]"
```

Before commit, a pre-commit hook will format the files.
Drop this in `.git/hooks/pre-commit`

```bash
    yapf -i -vv --recursive core
```
