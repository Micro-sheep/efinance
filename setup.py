
import pathlib
from setuptools import setup
HERE = pathlib.Path(__file__).parent


README = (HERE / "README.md").read_text()
REQUIREMENTS = (HERE/'requirements.txt').read_text().split()

setup(
    # 在 pypi 里面显示的项目名称
    name="efinance",
    # 版本
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
    # 要安装到 site-packages 的包名称
    packages=["efinance"],
    include_package_data=True,
    install_requires=REQUIREMENTS,
)
