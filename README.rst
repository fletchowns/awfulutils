Awful Utils: A set of utilities for the Something Awful forums
==============================================================

Features
--------

- Export thread to local disk for archival purposes
- Retrieve user details

Notice
------

This library is not affiliated with Something Awful LLC in any way

Installation
------------

You must have Python 3.2 or later installed. The exact commands used here may vary by operating system.

Using a Virtual Environment is always recommend to avoid installing packages system wide.

To create the Virtual Environment and activate it:

.. code-block:: bash
    $ mkdir ~/.virtualenvs
    $ python3 -m venv ~/.virtualenvs/awfulutils
    $ source ~/.virtualenvs/awfulutils

Now that your Virtual Environment is activated, you can install Awful Utils by running:

.. code-block:: bash

    $ pip install git+git://github.com/fletchowns/awfulutils.git

If a new version is pushed, you can upgrade yours by doing:

.. code-block:: bash

    $ pip install --upgrade git+git://github.com/fletchowns/awfulutils.git

Don't forget to activate your Virtual Environment whenever you open a new terminal

.. code-block:: bash
    $ source ~/.virtualenvs/awfulutils

Usage
------------

Use your web browser to figure out your bbuserid and bbpassword cookie values for forums.somethingawful.com

Now you should be able to run the command to export a thread:

.. code-block:: bash

    $ awful_export_thread --userid 38563 --session 99bd7c5025316dae9dcb6ea6d7366870 --threadid 2675400

Be sure to check for errors in the output! There might be a bug that leads to an incomplete export.

Unfortunately, you may see errors downloading images. You can double check the URL in your own browser, it may be a site that is long gone.

Log a ticket with the stack trace and the threadid you tried to export so we can fix it!

For a full list of arguments:

.. code-block:: bash

    $ awful_export_thread --help

Example Library Usage
-------------

Example of retrieving user details from Python code:

.. code-block:: pycon

    >>> from awfulutils.awfulclient import AwfulClient
    >>> awful_client = AwfulClient(38563, '99bd7c5025316dae9dcb6ea6d7366870')
    >>> awful_client.userinfo(27691).username
    'Lowtax'
