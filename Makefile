SHELL := /bin/bash


clean: clean-build clean-pyc

version:
	python setup.py --version

py_install:
	python setup.py install

clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	rm -rf .cache/
	rm -rf '*.egg-info/'
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

lint:
	flake8 sshless tests

dist: clean
	python setup.py sdist

pip: dist
	twine upload dist/*
	clean

tag_github_release:
	git tag `python setup.py --version`
	git push origin `python setup.py --version`


local: clean-build \
	py_install
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -rf '*.egg-info/'
