from setuptools import setup, find_packages

__version__ = "1.0"

setup(
    name="cliptiles_utils",
    version=__version__,
    author="CONTEC Co., Ltd.",
    description="cliptiles_utils",
    long_description='cliptiles_utils',
    long_description_content_type="text/markdown",
    url="https://www.contec.kr",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
    ],
)