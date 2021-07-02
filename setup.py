
import pathlib
from setuptools import setup

here = pathlib.Path(__file__).parent
# require = (here / "requirements.txt").read_text(encoding='utf-8').split()
require = ['requests', 'pandas', 'tqdm', 'retry', 'multitasking']
readme = (here / "README.md").read_text(encoding='utf-8')
setup(
    name="efinance",
    version="0.1",
    description="A finance tool to get stock,fund and futures data base on eastmoney",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/Micro-sheep/efinance",
    author="micro sheep",
    author_email="micro-sheep@outlook.com",
    license="MIT",
    platforms=['any'],
    keywords=['finance', 'quant', 'stock', 'fund', 'futures'],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    packages=["efinance"],
    install_requires=require,
    project_urls={
        'Documentation': 'https://micro-sheep.github.io/efinance',
        'Source': 'https://github.com/Micro-sheep/efinance',
    },
)
