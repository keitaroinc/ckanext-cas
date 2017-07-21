import logging
import helpers.cas as cas

from ckan import plugins

try:
    from ckan.tests import helpers
    from ckan.tests import factories
except ImportError:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories

log = logging.getLogger(__name__)

cas.serve()


class ActionBase(object):
    @classmethod
    def setup_class(self):
        if not plugins.plugin_loaded('cas'):
            plugins.load('cas')

    def setup(self):
        helpers.reset_db()

    @classmethod
    def teardown_class(self):
        if plugins.plugin_loaded('cas'):
            plugins.unload('cas')


class TestCASClient(ActionBase):
    @classmethod
    def setup(cls):
        pass

    def test_login_with_invalid_credentials(self):
        pass

    def test_login_with_valid_credentials(self):
        pass

    def test_application_logout(self):
        pass

    def test_single_logout(self):
        pass
