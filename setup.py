from setuptools import setup, find_packages
import os

# Read the contents of your README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="apkscraper",  # This is the name that will appear on PyPI
    version="1.0.0",
    author="Spectre",
    author_email="spectre@bugbounty.local",
    description="An enterprise-grade, multi-threaded historical APK extraction pipeline.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sumanrox/apkscrapper",
    project_urls={
        "Bug Tracker": "https://github.com/sumanrox/apkscrapper/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "Topic :: Utilities",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.1",
        "beautifulsoup4>=4.9.3"
    ],
    entry_points={
        "console_scripts": [
            "apkscraper=apkscraper.__main__:main",
        ]
    },
)
