
import pathlib
from setuptools import setup
HERE = pathlib.Path(__file__).parent


README = (HERE / "README.md").read_text()
REQUIREMENTS = (HERE/'requirements.txt').read_text().split()

setup(
    # name in pypi
    name="efinance",
    version="0.1",
    description="A finance tool for crawl stock,fund and futures data base on eastmoney",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/Micro-sheep/efinance",
    author="micro sheep",
    author_email="micro-sheep@outlook.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    # package to be installed in  site-packages
    packages=["efinance"],
    include_package_data=True,
    install_requires=REQUIREMENTS,
)
