import codecs
import os.path
import sys
import unittest

from setuptools import setup, find_packages
from setuptools.command.test import test as TestClass

here = os.path.abspath(os.path.dirname(__file__))
readme_md = os.path.join(here, 'README.md')

# Get the package description from the README.md file
with codecs.open(readme_md, encoding='utf-8') as f:
    long_description = f.read()

version = "0.1.18"


class TestCommand(TestClass):
    user_options = []
    __dir__ = os.path.dirname(os.path.realpath(__file__))

    def initialize_options(self):
        super().initialize_options()
        sys.path.insert(0, os.path.join(self.__dir__, "tests"))

    def run_tests(self):
        test_suite = unittest.TestLoader().discover(".", pattern="test_*.py")
        result = unittest.TextTestRunner(buffer=True).run(test_suite)
        sys.exit(not result.wasSuccessful())


cmdclass = {"test": TestCommand}

try:
    long_description = open("README.rst").read()
except IOError:
    long_description = ""

setup(
    name="perceval-gitlink",
    version="0.1.0",
    description="Bundle of Perceval backends for Gitlink",
    license="GPLV3",
    author="PickupRAIN",
    author_email="zhoushiyu21@nudt.edu.cn",
    long_description=long_description,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    keywords="development repositories analytics for gitlink",
    packages=["perceval", "perceval.backends", "perceval.backends.gitlink"],
    namespace_packages=["perceval", "perceval.backends"],
    setup_requires=["wheel", "pandoc"],
    tests_require=["httpretty>=0.9.6"],
    install_requires=[
        "requests>=2.7.0",
        "grimoirelab-toolkit>=0.1.9",
        "perceval>=0.12.12",
    ],
    cmdclass=cmdclass,
    zip_safe=False,
)
