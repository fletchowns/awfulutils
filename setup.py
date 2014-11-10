from distutils.core import setup
from awfulutils import __version__

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name='awfulutils',
    packages=['awfulutils'],
    version=__version__,
    description='A set of utilities for the Something Awful forums',
    long_description = readme(),
    author='Greg Barker',
    author_email='fletch@fletchowns.net',
    url='https://github.com/fletchowns/awfulutils',
    scripts = ['bin/awful_export_thread.py'],
    keywords=['something awful'],
    install_requires=[
        'html5lib',
        'requests',
        'beautifulsoup4'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Communications :: Chat',
        'Topic :: Internet',
        'Topic :: Multimedia',
        'Topic :: Utilities',
    ]
)