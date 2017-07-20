# -*- coding: utf-8 -
try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

import logging
import requests as rq
import ckan.plugins as p
import ckan.plugins.toolkit as t
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as l

render = base.render
abort = base.abort
redirect = base.redirect

from urllib import urlencode
from ckanext.cas.controller import CTRL

log = logging.getLogger(__name__)


class CASClientPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IAuthenticator, inherit=True)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IConfigurable)

    USER_ATTR_MAP = {}
    TICKET_KEY = None
    SERVICE_KEY = None
    SERVICE_VALIDATION_URL = None
    SAML_VALIDATION_URL = None
    CAS_LOGOUT_URL = None
    CAS_LOGIN_URL = None
    CAS_COOKIE_NAME = None

    def configure(self, config_):

        user_mapping = t.aslist(config_.get('ckanext.cas.user_mapping'))
        for attr in user_mapping:
            key, val = attr.split('~')
            self.USER_ATTR_MAP.update({key: val})

        if not any(self.USER_ATTR_MAP):
            raise RuntimeError, 'Attribute map is required for plugin: {0}'.format(self.name)

        if 'email' not in self.USER_ATTR_MAP.keys():
            raise RuntimeError, '"email" attribute mapping is required for plugin: {0}'.format(self.name)

        self.CAS_LOGIN_URL = config.get('ckanext.cas.login_url', 'http://localhost:8000/login')
        self.CAS_LOGOUT_URL = config.get('ckanext.cas.logout_url', 'http://localhost:8000/login')
        self.CAS_COOKIE_NAME = config.get('ckanext.cas.cookie_name', 'sessionid')
        self.TICKET_KEY = config.get('ckanext.cas.ticket_key', 'ticket')
        self.SERVICE_KEY = config.get('ckanext.cas.service_key', 'service')
        self.SERVICE_VALIDATION_URL = config.get('ckanext.cas.service_validation_url',
                                                 'http://localhost:8000/serviceValidate')
        self.SAML_VALIDATION_URL = config.get('ckanext.cas.saml_validation_url',
                                              'http://localhost:8000/samlValidate')

    # IConfigurer

    def update_config(self, config_):
        t.add_template_directory(config_, 'templates')
        t.add_public_directory(config_, 'public')
        t.add_resource('fanstatic', 'cas')

    def before_map(self, map):
        map.connect('cas_callback', '/cas/callback', controller=CTRL, action='cas_callback')
        map.connect('cas_logout', '/cas/logout', controller=CTRL, action='cas_logout')
        return map

    def identify(self):
        log.debug('IN IDENTIFY METHOD')
        log.debug(t.c.user)

    def login(self):
        log.debug('PLUGIN LOGIN')
        LOGIN_URL = 'http://localhost:8000/login?service=http://localhost:5000/cas/callback'
        redirect(LOGIN_URL)

    def logout(self):
        c = t.c
        log.debug('PLUGIN LOGOUT')
        q = rq.get('http://localhost:8000/logout', cookies=t.request.cookies)
        log.debug(q.status_code)

    def abort(self, status_code, detail, headers, comment):
        c = t.c
        log.debug('PLUGIN ABORT')
        log.debug(c)
