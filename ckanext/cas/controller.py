# -*- coding: utf-8 -
try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

import logging
import requests as rq
import ckan.plugins.toolkit as t
import ckan.lib.base as base
import ckan.plugins as p
import ckan.model as m
import ckan.logic as l
import ckan.lib.helpers as h

from ckan.controllers.user import UserController, set_repoze_user
from lxml import etree, objectify
from uuid import uuid4

log = logging.getLogger(__name__)

CTRL = 'ckanext.cas.controller:CASController'

render = base.render
abort = base.abort
redirect = base.redirect


class CASController(UserController):
    def cas_logout(self):
        log.debug('CAS LOGOUT CALLBACK')
        log.debug(t.request)
        # TODO: Check if logout was successful in CAS server
        url = h.url_for(controller='user', action='logged_out_page',
                        __ckan_no_root=True)
        h.redirect_to(getattr(t.request.environ['repoze.who.plugins']['friendlyform'], 'logout_handler_path') + '?came_from=' + url)

    def cas_callback(self, **kwargs):
        log.debug('CAS CALLBACK')
        cas_plugin = p.get_plugin('cas')
        if t.request.method.lower() == 'get':
            ticket = t.request.params.get(cas_plugin.TICKET_KEY)
            log.debug('Validating ticket: {0}'.format(ticket))
            q = rq.get(cas_plugin.SERVICE_VALIDATION_URL,
                       params={cas_plugin.TICKET_KEY: ticket,
                               cas_plugin.SERVICE_KEY: config.get('ckan.site_url') + '/cas/callback'})

            root = objectify.fromstring(q.content)
            try:
                if hasattr(root.authenticationSuccess, 'user'):
                    username = root.authenticationSuccess.user
                    success = True
            except AttributeError:
                success, username = False, None

            try:
                failure = root.authenticationFailure
            except AttributeError:
                failure = False

            if failure:
                # Validation failed - ABORT
                log.debug('Validation of ticket {0} failed with message: {1}'.format(ticket, failure))

            log.debug('Validation of ticket {0} succedded. Authenticated user: {1}'.format(ticket, success))
            user = m.User.get(username.text)
            if user is None:
                attrs = root.authenticationSuccess.attributes
                fullname = getattr(attrs, cas_plugin.USER_ATTR_MAP['fullname'])
                email = getattr(attrs, cas_plugin.USER_ATTR_MAP['email'])
                name = username.text
                if 'user' in cas_plugin.USER_ATTR_MAP.keys():
                    name = getattr(attrs, cas_plugin.USER_ATTR_MAP['user'])
                sysadmin = False
                if 'sysadmin' in cas_plugin.USER_ATTR_MAP.keys():
                    sysadmin = getattr(attrs, cas_plugin.USER_ATTR_MAP['sysadmin'])

                data_dict = {'name': unicode(name),
                             'email': email.text,
                             'fullname': fullname.text,
                             'password': uuid4().hex}
                try:
                    user_obj = l.get_action('user_create')({'ignore_auth': True}, data_dict)
                except Exception as e:
                    log.debug('Error while creating user')
                    log.debug(e)

                if sysadmin:
                    # TODO: Make user sysadmin
                    print sysadmin

                set_repoze_user(user_obj['name'])
                redirect(t.h.url_for(controller='user', action='dashboard', id=user_obj['name']))

            else:
                set_repoze_user(user.name)
                redirect(t.h.url_for(controller='user', action='dashboard', id=user.name))

        elif t.request.method.lower() == 'post':
            log.debug(t.request)
        else:
            log.debug('NotImplemented: {0}'.format(t.request.method))
