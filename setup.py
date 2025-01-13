from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

# Read long description from README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="meridian-news-aggregator",
    version="0.1.0",
    author="Stephen A. Hedrick",
    author_email="Stephen@wavebound.io",
    description="An intelligent RSS news aggregator with advanced clustering and ranking capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CartesianXR7/meridian",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Text Processing :: General",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=required,
    entry_points={
        'console_scripts': [
            'meridian=meridian.aggregator:main',
        ],
    },
    include_package_data=True,
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=22.0',
            'flake8>=3.9',
        ],
    },
)
