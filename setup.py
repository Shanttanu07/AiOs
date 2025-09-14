#!/usr/bin/env python3
"""AIOX setup script"""

from setuptools import setup, find_packages

setup(
    name="aiox",
    version="0.1.0",
    description="AI Operating System - Natural Language to Executable Code",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "aiox=aiox.cli:main",
        ],
    },
    python_requires=">=3.8",
    install_requires=[
        "jsonschema",
        "windows-curses; platform_system=='Windows'",
    ],
)