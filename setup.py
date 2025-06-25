import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 8):
    sys.exit('Sorry, Python < 3.8 is not supported.')

with open("README.md", "r") as fh:
    long_description = fh.read()
    
setup(
    name="hivelink",
    packages=[package for package in find_packages()],
    version="0.1",
    license="GPL",
    description="Hivelink",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Frogmane",
    author_email="",
    url="https://github.com/xznhj8129/hivelink",
    download_url="",
    include_package_data=True,
    keywords=['udp','meshtastic','manet','mavlink'],
    install_requires=['geographiclib','mgrs','geojson','crcmod','msgpack','asyncio'],
    classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Intended Audience :: Education',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Framework :: Robot Framework :: Library',
          'Topic :: Education',
    ]
)