import pathlib

from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent
# require = (here / "requirements.txt").read_text(encoding='utf-8').split()
require = ['requests', 'rich', 'jsonpath', 'pandas', 'tqdm', 'retry', 'multitasking', 'bs4']
readme = (here / "README.md").read_text(encoding='utf-8')
about = {}
exec((here / 'efinance' / '__version__.py').read_text(encoding='utf-8'), about)
setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme,
    long_description_content_type="text/markdown",
    url=about['__url__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    license="MIT",
    platforms=['any'],
    keywords=about['__keywords__'],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    packages=find_packages(),
    install_requires=require,
    project_urls=about['__project_urls__'],
)
