import re
from os.path import join as join_path

import setuptools

with open(join_path("zetuptools", "__init__.py"), encoding="utf8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setuptools.setup(
    name='zetuptools',
    version=version,
    author='Zeke Marffy',
    author_email='zmarffy@yahoo.com',
    packages=setuptools.find_packages(),
    url='https://github.com/zmarffy/zetuptools',
    license='MIT',
    description='Extra setuptools stuff',
    python_requires='>=3.6',
    long_description=open('README.txt').read(),
    long_description_content_type='text/plain',
    install_requires=[
        'vermin',
        'docker',
        'zmtools>=1.7.0'
    ],
)
