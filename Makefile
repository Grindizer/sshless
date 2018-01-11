SHELL := /bin/bash


clean: clean-build clean-pyc

version:
	python setup.py --version

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

tag_github_release:
	git tag "v$(cat VERSION)"
	git push origin "v$(cat VERSION)"


local: clean-build
	python setup.py install
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -rf *.egg-info/
