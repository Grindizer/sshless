#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup


with open("README.rst") as readme_file:
    readme = readme_file.read()


with open("VERSION") as version_file:
    version = version_file.read().strip()

with open("requirements.txt") as requirements_file:
    requirements = [
        requirement for requirement in requirements_file.read().split("\n")
        if requirement != ""
    ]

setup_requirements = [
    "pytest-runner==2.6.2"
]

setup(
    name="sshless",
    version=version,
    description="sshless using AWS SSM",
    long_description=readme,
    author="giuliocalzolari",
    author_email="gc@hide.me",
    license='MIT',
    url="https://github.com/giuliocalzolari/sshless",
    packages=[
        "sshless"
    ],
    package_dir={
        "sshless": "sshless"
    },
    py_modules=["sshless"],
    entry_points="""
        [console_scripts]
        sshless=sshless.cli:cli
    """,
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,
    keywords="sshless",
    classifiers=[
        "Development Status :: 5 - Testing",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Environment :: Console",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    test_suite="tests",
    setup_requires=setup_requirements
)
