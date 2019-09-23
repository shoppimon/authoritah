# Simple makefile for authoritah - put common tasks here

SHELL := bash
PIP := pip
PYTEST := py.test


test:
	$(PIP) install -r dev-requirements.txt .
	$(PYTEST) --cov-report xml --cov=authoritah
