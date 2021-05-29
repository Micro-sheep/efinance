
from setuptools import setup
setup(
    name='efinance',
    author='sheep',
    platforms=['any'],
    install_requires=['pandas',
                      'tqdm',
                      'retry',
                      'requests>=2.20',
                      'multitasking>=0.0.7'],

)
