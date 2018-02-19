.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org/polarp/ckanext-cas.svg?branch=master
    :target: https://travis-ci.org/polarp/ckanext-cas

.. image:: https://coveralls.io/repos/polarp/ckanext-cas/badge.svg
  :target: https://coveralls.io/r/polarp/ckanext-cas


=============
ckanext-cas
=============

.. Put a description of your extension here:
   What does it do? What features does it have?
   Consider including some screenshots or embedding a video!


------------
Special Thanks
------------
Special thanks to `Neogeo Technologies <http://www.neogeo-online.net>`_ for their contribution in making of this plugin.

------------
Requirements
------------

This extension works with CKAN version 2.6 and above.


------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-cas:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-cas Python package into your virtual environment::

     pip install ckanext-cas
     pip install -r ckanext-cas/requirements.txt

3. Add ``cas`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config Settings
---------------

In order to configure CKAN to use CAS you must setup the following configuration options::

    # User attributes mapping (required)
    # ``email`` and ``user`` mappings are required
    ckanext.cas.user_mapping = email~email user~username fullname~full_name sysadmin~is_superuser

    # If you need to combine attributes (note fullname)
    ckanext.cas.user_mapping = email~email user~username fullname~first_name+last_name sysadmin~is_superuser

    # CAS login URL (required)
    ckanext.cas.login_url = http://mamacas.django.com/login

    # CAS logout URL (required)
    ckanext.cas.logout_url = http://mamacas.django.com/logout

    # CKAN application URL (required)
    # The URL through which users are interacting with the application
    ckanext.cas.application_url = https://ckan-demo.com

    # CAS single sign out (optional)
    ckanext.cas.single_sign_out = true

    # CAS service validation URL (conditional)
    # Either ``ckanext.cas.service_validation_url`` or ``ckanext.cas.saml_validation_url`` must be configured.
    ckanext.cas.service_validation_url = http://mamacas.django.com/serviceValidate

    # CAS SAML validation URL (conditional)
    # Either ``ckanext.cas.service_validation_url`` or ``ckanext.cas.saml_validation_url`` must be configured.
    ckanext.cas.saml_validation_url = http://mamacas.django.com/samlValidate

    # Registration URL (optional)
    # Overrides the default registration page of CKAN
    ckanext.cas.register_url = http://register.django.com

    # Unsuccessful login redirect URL (optional)
    # When login is unsuccessful redirect users to this URL
    ckanext.cas.unsuccessful_login_redirect_url

    # Time (in seconds) for checkup if the user is authenticated in CAS (optional)
    # defaults to 600
    ckanext.cas.login_checkup_time = 600

    # Name of the cookie for login checkup (optional)
    # defaults to cas_login_check
    ckanext.cas.login_checkup_cookie = cas_login_check

    # Enable/disable certificate verification when making requests to Mama-Cas
    ckanext.cas.verify_certificate = true


Make sure you have configured ``django-mama-cas`` properly i.e. ::

    MAMA_CAS_SERVICES = [
        {
            'SERVICE': '^https://ckan-demo.com',
            'CALLBACKS': [
                'mama_cas.callbacks.user_name_attributes',
                'mama_cas.callbacks.user_model_attributes'
            ],
            'LOGOUT_ALLOW': True,
            'LOGOUT_URL': 'https://ckan-demo.com/cas/logout'
        },
    ]

**NOTE:** If you use SAML as validation method for CAS have in mind that CKAN and django must be accessed over SSL.

The current version of ``django-mama-cas`` has a bug when you use SAML as validation method since it is unable
to serialize user attribute types that are different from string.

`Pull request <https://github.com/jbittel/django-mama-cas/pull/44>`_ has been submitted
but until it has been approved and merged you can use the following `fork <https://github.com/keitaroinc/django-mama-cas/tree/saml-response-errors>`_ of ``django-mama-cas``.


------------------------
Development Installation
------------------------

To install ckanext-cas for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/keitaroinc/ckanext-cas.git
    cd ckanext-cas
    python setup.py develop
    pip install -r dev-requirements.txt && pip install -r requirements.txt


-----------------
Running the Tests
-----------------

In order to run the tests you must have django instance running with mama cas enabled as well as running CKAN instance.
Both applications have to be configured according to the documentation.

You might need to edit ``test.ini`` and update configuration options to match the ones from your running instances of django and CKAN.
To execute the tests make sure you activated the virtual environment in which you've installed CKAN and type::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.cas --cover-inclusive --cover-erase --cover-tests


---------------------------------
Registering ckanext-cas on PyPI
---------------------------------

ckanext-cas should be availabe on PyPI as
https://pypi.python.org/pypi/ckanext-cas. If that link doesn't work, then
you can register the project on PyPI for the first time by following these
steps:

1. Create a source distribution of the project::

     python setup.py sdist

2. Register the project::

     python setup.py register

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the first release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags


----------------------------------------
Releasing a New Version of ckanext-cas
----------------------------------------

ckanext-cas is availabe on PyPI as https://pypi.python.org/pypi/ckanext-cas.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Create a source distribution of the new version::

     python setup.py sdist

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.2 then do::

       git tag 0.0.2
       git push --tags
