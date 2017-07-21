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

from ckanext.cas.db import is_ticket_valid

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
    CAS_VERSION = None

    def configure(self, config_):

        user_mapping = t.aslist(config_.get('ckanext.cas.user_mapping'))
        for attr in user_mapping:
            key, val = attr.split('~')
            self.USER_ATTR_MAP.update({key: val})

        if not any(self.USER_ATTR_MAP):
            raise RuntimeError, 'Attribute map is required for plugin: {0}'.format(self.name)

        if 'email' not in self.USER_ATTR_MAP.keys():
            raise RuntimeError, '"email" attribute mapping is required for plugin: {0}'.format(self.name)

        if config.get('ckanext.cas.service_validation_url', None) and config.get('ckanext.cas.saml_validation_url', None):
            raise RuntimeError, 'Only one of "ckanext.cas.service_validation_url" and "ckanext.cas.saml_validation_url" should be set'
        elif not config.get('ckanext.cas.service_validation_url', None) and not config.get('ckanext.cas.saml_validation_url', None):
            raise RuntimeError, 'One of "ckanext.cas.service_validation_url" or "ckanext.cas.saml_validation_url" is required for plugin: {0}'.format(self.name)

        if not config.get('ckanext.cas.login_url', None):
            raise RuntimeError, '"ckanext.cas.login_url" is required for plugin: {0}'.format(self.name)

        if not config.get('ckanext.cas.logout_url', None):
            raise RuntimeError, '"ckanext.cas.logout_url" is required for plugin: {0}'.format(self.name)

        if config.get('ckanext.cas.service_validation_url', None):
            self.SERVICE_VALIDATION_URL = config.get('ckanext.cas.service_validation_url')
            self.CAS_VERSION = 2
        elif config.get('ckanext.cas.saml_validation_url', None):
            self.SAML_VALIDATION_URL = config.get('ckanext.cas.saml_validation_url')
            self.CAS_VERSION = 3

        self.CAS_LOGIN_URL = config.get('ckanext.cas.login_url')
        self.CAS_LOGOUT_URL = config.get('ckanext.cas.logout_url')
        self.CAS_COOKIE_NAME = config.get('ckanext.cas.cookie_name', 'sessionid')
        self.TICKET_KEY = config.get('ckanext.cas.ticket_key', 'ticket')
        self.SERVICE_KEY = config.get('ckanext.cas.service_key', 'service')

    # IConfigurer

    def update_config(self, config_):
        t.add_template_directory(config_, 'templates')
        t.add_public_directory(config_, 'public')
        t.add_resource('fanstatic', 'cas')

    def before_map(self, map):
        map.connect('cas_callback', '/cas/callback', controller=CTRL, action='cas_callback')
        map.connect('cas_saml_callback', '/cas/saml_callback', controller=CTRL, action='cas_saml_callback')
        map.connect('cas_logout', '/cas/logout', controller=CTRL, action='cas_logout')
        return map

    def identify(self):
        log.debug('IN IDENTIFY METHOD')

        environ = t.request.environ
        remote_user = environ.get('REMOTE_USER', None)
        log.debug(remote_user)
        if remote_user and not is_ticket_valid(remote_user):
            log.debug('User logged out of CAS Server')
            url = h.url_for(controller='user', action='logged_out_page',
                        __ckan_no_root=True)
            h.redirect_to(getattr(t.request.environ['repoze.who.plugins']['friendlyform'], 'logout_handler_path') + '?came_from=' + url)

    def _generate_login_url(self):
        if self.CAS_VERSION == 2:
            return self.CAS_LOGIN_URL + '?service=' + config.get('ckanext.cas.application_url') + '/cas/callback'
        elif self.CAS_VERSION == 3:
            return self.CAS_LOGIN_URL + '?service=' + config.get('ckanext.cas.application_url') + '/cas/saml_callback'

    def login(self):
        log.debug('PLUGIN LOGIN')
        cas_login_url = self._generate_login_url()
        redirect(cas_login_url)

    def logout(self):
        log.debug('PLUGIN LOGOUT')
        if t.asbool(config.get('ckanext.cas.single_sign_out')):
            cas_logout_url = self.CAS_LOGOUT_URL + '?service=' + config.get('ckanext.cas.application_url') + '/cas/logout'
            redirect(cas_logout_url)
        # TODO: Refactor into helper
        url = h.url_for(controller='user', action='logged_out_page',
                        __ckan_no_root=True)
        h.redirect_to(getattr(t.request.environ['repoze.who.plugins']['friendlyform'], 'logout_handler_path') + '?came_from=' + url)

    def abort(self, status_code, detail, headers, comment):
        c = t.c
        log.debug('PLUGIN ABORT')
        log.debug(c)
