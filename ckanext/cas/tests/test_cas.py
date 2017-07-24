import logging
import requests as rq

from lxml import html
from ckan import plugins
from ckan.common import config

try:
    from ckan.tests import helpers
    from ckan.tests import factories
except ImportError:
    from ckan.new_tests import helpers
    from ckan.new_tests import factories

log = logging.getLogger(__name__)

USERS = {
    'valid': {
        'username': 'admin',
        'password': 'admin',
        'fullname': 'Admin User'
    },
    'invalid': {
        'username': 'invalid',
        'password': 'user'
    }
}


class TestBase(object):
    @classmethod
    def setup_class(self):
        if not plugins.plugin_loaded('cas'):
            plugins.load('cas')

    def setup(self):
        self.ckan_url = config.get('ckanext.cas.application_url')
        self.cas_login_url = config.get('ckanext.cas.login_url')
        self.cas_logout_url = config.get('ckanext.cas.logout_url')

    @classmethod
    def teardown_class(self):
        if plugins.plugin_loaded('cas'):
            plugins.unload('cas')


class TestCASClient(TestBase):
    def test_invalid_login(self):
        r = rq.get(self.ckan_url + 'user/login')
        data_dict = USERS.get('invalid')
        doc = html.fromstring(r.content)
        csrf_token = doc.xpath('//input[@name="csrfmiddlewaretoken"]/@value')[0]
        data_dict.update({'csrfmiddlewaretoken': csrf_token})

        r = rq.post(self.cas_login_url + '?service={0}'.format(self.ckan_url + 'cas/callback'),
                    data=data_dict,
                    cookies=r.cookies)

        assert 'The username or password is not correct' in r.content

    def test_service_login_with_valid_credentials(self):
        r = rq.get(self.ckan_url + '/user/login')
        data_dict = USERS.get('valid')
        doc = html.fromstring(r.content)
        csrf_token = doc.xpath('//input[@name="csrfmiddlewaretoken"]/@value')[0]
        data_dict.update({'csrfmiddlewaretoken': csrf_token})

        r = rq.post(self.cas_url + '?service={0}'.format(self.ckan_url + 'cas/callback'),
                    data=data_dict,
                    cookies=r.cookies,
                    allow_redirects=False)

        # Permit redirects to save the auth cookie
        sessionid = r.cookies.get('sessionid', None)
        r = rq.get(r.headers['Location'], cookies=r.cookies, allow_redirects=False)
        auth_tkt = r.cookies.get('auth_tkt', None)
        r = rq.get(r.headers['Location'], cookies=r.cookies)

        assert '<a href="/dashboard">Dashboard</a>' in r.content
        assert '<span class="username">{0}</span>'.format(data_dict['fullname']) in r.content

    def test_saml_login_with_valid_credentials(self):
        pass

    def test_application_logout(self):
        pass

    def test_single_logout(self):
        r = rq.get(self.ckan_url + '/user/login')
        data_dict = USERS.get('valid')
        doc = html.fromstring(r.content)
        csrf_token = doc.xpath('//input[@name="csrfmiddlewaretoken"]/@value')[0]
        data_dict.update({'csrfmiddlewaretoken': csrf_token})

        r = rq.post(self.cas_login_url + '?service={0}'.format(self.ckan_url + 'cas/callback'),
                    data=data_dict,
                    cookies=r.cookies,
                    allow_redirects=False)

        sessionid = r.cookies.get('sessionid', None)
        r = rq.get(r.headers['Location'], cookies=r.cookies, allow_redirects=False)

        auth_tkt = r.cookies.get('auth_tkt', None)
        r = rq.get(r.headers['Location'], cookies={'auth_tkt': auth_tkt[1:-1]}, allow_redirects=False)

        assert '<a href="/dashboard">Dashboard</a>' in r.content
        assert '<span class="username">{0}</span>'.format(data_dict['fullname']) in r.content

        logout_url = self.cas_logout_url + '?service={0}'.format(self.ckan_url + 'cas/logout')
        r = rq.get(logout_url, cookies={'sessionid': sessionid}, allow_redirects=False)

        r = rq.get(self.ckan_url + 'dashboard', cookies={'auth_tkt': auth_tkt[1:-1]}, allow_redirects=False)
        assert '<a href="/dashboard">Dashboard</a>' not in r.content
        assert '<span class="username">{0}</span>'.format(data_dict['fullname']) not in r.content
