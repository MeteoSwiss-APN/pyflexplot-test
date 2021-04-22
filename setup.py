"""Set up the project."""
# Standard library
from typing import List
from typing import Sequence

# Third-party
from setuptools import find_packages
from setuptools import setup


def read_present_files(paths: Sequence[str]) -> str:
    """Read the content of those files that are present."""
    contents: List[str] = []
    for path in paths:
        try:
            with open(path, "r") as f:
                contents += ["\n".join(map(str.strip, f.readlines()))]
        except FileNotFoundError:
            continue
    return "\n\n".join(contents)


description_files = [
    "README",
    "README.rst",
    "README.md",
    "HISTORY",
    "HISTORY.rst",
    "HISTORY.md",
]

metadata = {
    "name": "pyflexplot-test",
    "version": "0.4.0",
    "description": "Compare the plots created by two versions of PyFlexPlot.",
    "long_description": read_present_files(description_files),
    "author": "Stefan Ruedisuehli",
    "author_email": "stefan.ruedisuehli@meteoswiss.ch",
    "url": "https://github.com/MeteoSwiss-APN/pyflexplot-test",
    "keywords": "pyflexplot-test",
    "classifiers": [
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
}

python = ">= 3.7"

# Runtime dependencies (unpinned: only critical version restrictions)
requirements = [
    "click >= 7.1",
    "gitpython >= 3.1",
    "typing_extensions",
]

scripts = [
    "pyflexplot-test=pyflexplot_test.cli:cli",
]

setup(
    python_requires=python,
    install_requires=requirements,
    entry_points={"console_scripts": scripts},
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_save=False,
    **metadata,
)
