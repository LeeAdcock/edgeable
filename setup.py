import pathlib
from setuptools import setup
import os

# The directory containing this file
HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()

setup(
    name="edgeable",
    version="0.1.TRAVIS_BUILD_NUMBER",
    description="Easy to use, in memory, peristable graph database.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/leeadcock/edgeable",
    author="Lee Adcock",
    author_email="lee@katieandlee.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["edgeable"],
    include_package_data=True,
    install_requires=["pytest"],
)
