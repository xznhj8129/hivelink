import sys
from setuptools import find_packages, setup

if sys.version_info < (3, 8):
    sys.exit("Sorry, Python < 3.8 is not supported.")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="hivelink",
    packages=find_packages(),
    version="0.0.1",
    license="GPL",
    description="OCCID node-to-node delivery over simple or heterogeneous links",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Frogmane",
    author_email="",
    url="https://github.com/xznhj8129/hivelink",
    include_package_data=True,
    keywords=["udp", "mesh", "meshtastic", "occid"],
    install_requires=[
        "crcmod",
        "msgpack",
        "pydantic>=2",
    ],
    extras_require={
        "meshtastic": ["frogtastic"],
        "cli": ["prompt-toolkit"],
        "all": ["frogtastic", "prompt-toolkit"],
    },
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
    ],
)
