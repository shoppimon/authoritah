# Simple makefile for authoritah - put common tasks here

SHELL := bash
PIP := pip
PYTHON := python
PYTEST := py.test


test:
	$(PIP) install -r dev-requirements.txt .
	$(PYTEST) --cov-report xml --cov=authoritah

wheel:
	$(PIP) install -U pip wheel twine
	$(PYTHON) setup.py bdist_wheel --universal
