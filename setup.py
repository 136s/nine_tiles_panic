#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name="nine_tiles_panic",
    version="0.1.0",
    description="Find the best town for Nine Tiles Panic by brute force.",
    url="https://github.com/136s/nine_tiles_panic",
    packages=find_packages(exclude=("tests", "docs")),
    package_data={"nine_tiles_panic": ["data/imgs/*.png"]},
    install_requires=["networkx", "numpy", "pillow"],
    python_requires=">=3.9.12",
)
