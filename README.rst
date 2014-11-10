Awful Utils: A set of utilities for the Something Awful forums
==============================================================

Features
--------

- Retrieve user details
- Export thread to local disk

Notice
------

This library is not affiliated with Something Awful LLC in any way

Installation
------------

You must have Python 3.2 or later installed

To install Awful Utils, simply:

.. code-block:: bash

    $ pip install git+git://github.com/fletchowns/awfulutils.git


Example Usage
-------------

First, obtain the bbuserid and bbpassword cookie values for domain forums.somethingawful.com from your browser.

Retrieve user details from Python:

.. code-block:: pycon

    >>> from awfulutils.awfulclient import AwfulClient
    >>> awful_client = AwfulClient(38563, '99bd7c5025316dae9dcb6ea6d7366870')
    >>> awful_client.userinfo(27691).username
    'Lowtax'

Export thread to local disk from command line:

.. code-block:: bash

    $ awful_export_thread --userid 38563 --session 99bd7c5025316dae9dcb6ea6d7366870 --threadid 2675400