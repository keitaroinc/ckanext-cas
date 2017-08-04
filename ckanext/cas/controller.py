# -*- coding: utf-8 -
try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

import datetime
import logging
import time
import urllib
from uuid import uuid4

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as l
import ckan.model as m
import ckan.plugins as p
import ckan.plugins.toolkit as t
import requests as rq
from ckan.controllers.user import UserController, set_repoze_user
from ckanext.cas.db import delete_entry, delete_user_entry, insert_entry
from lxml import etree, objectify

log = logging.getLogger(__name__)

CTRL = 'ckanext.cas.controller:CASController'

render = base.render
abort = base.abort
redirect = base.redirect

CAS_NAMESPACE = 'urn:oasis:names:tc:SAML:2.0:protocol'
XML_NAMESPACES = {'samlp': CAS_NAMESPACE}
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


class CASController(UserController):
    def cas_logout(self):
        log.debug('Invoked "cas_logout" method.')

        data = t.request.POST
        message = data.get('logoutRequest', None)

        if not message:
            return False

        parsed = etree.fromstring(urllib.unquote(message))
        session_index = parsed.find('samlp:SessionIndex', XML_NAMESPACES)
        if session_index is not None:
            delete_entry(session_index.text)

        url = h.url_for(controller='user', action='logged_out_page',
                        __ckan_no_root=True)
        h.redirect_to(getattr(t.request.environ['repoze.who.plugins']['friendlyform'],
                              'logout_handler_path') + '?came_from=' + url)

    def _generate_saml_request(self, ticket_id):
        prefixes = {'SOAP-ENV': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'samlp': 'urn:oasis:names:tc:SAML:1.0:protocol'}

        def _generate_ns_element(prefix, element):
            return etree.QName(prefixes[prefix], element)

        for prefix, uri in prefixes.items():
            etree.register_namespace(prefix, uri)

        envelope = etree.Element(_generate_ns_element('SOAP-ENV', 'Envelope'))
        etree.SubElement(envelope, _generate_ns_element('SOAP-ENV', 'Header'))
        body = etree.SubElement(envelope, _generate_ns_element('SOAP-ENV', 'Body'))

        request = etree.Element(_generate_ns_element('samlp', 'Request'))
        request.set('MajorVersion', '1')
        request.set('MinorVersion', '1')
        request.set('RequestID', uuid4().hex)
        request.set('IssueInstant', datetime.datetime.utcnow().strftime(DATETIME_FORMAT))
        artifact = etree.SubElement(request, _generate_ns_element('samlp', 'AssertionArtifact'))
        artifact.text = ticket_id

        body.append(request)
        return etree.tostring(envelope, encoding='UTF-8')

    def cas_saml_callback(self, **kwargs):
        log.debug('Invoked "cas_saml_callback" method.')
        cas_plugin = p.get_plugin('cas')
        if t.request.method.lower() == 'get':
            ticket = t.request.params.get(cas_plugin.TICKET_KEY)
            if not ticket:
                t.response.set_cookie(cas_plugin.LOGIN_CHECKUP_COOKIE, str(time.time()),
                                      max_age=cas_plugin.LOGIN_CHECKUP_TIME)
                next_url = t.request.params.get('next', '/')
                redirect(cas_plugin.CAS_APP_URL + next_url)

            log.debug('Validating ticket: {0}'.format(ticket))
            q = rq.post(cas_plugin.SAML_VALIDATION_URL + '?TARGET={0}/cas/saml_callback'.format(cas_plugin.CAS_APP_URL),
                        data=self._generate_saml_request(ticket),
                        verify=False)  # TODO: Change to true

            root = objectify.fromstring(q.content)
            failure = False
            try:
                if root['Body']['{urn:oasis:names:tc:SAML:1.0:protocol}Response']['Status']['StatusCode'].get(
                        'Value') == 'samlp:Success':
                    user_attrs = cas_plugin.USER_ATTR_MAP
                    cas_attributes = [x for x in root['Body']['{urn:oasis:names:tc:SAML:1.0:protocol}Response'][
                        '{urn:oasis:names:tc:SAML:1.0:assertion}Assertion']['AttributeStatement']['Attribute']]
                    data_dict = {}
                    attributes = {key.get('AttributeName'): key['AttributeValue'].text for key in cas_attributes}

                    for key, val in user_attrs.items():
                        if type(val) == list:
                            data_dict[key] = ' '.join([attributes.get(x, '') for x in val])
                        else:
                            data_dict[key] = attributes.get(val, '')

                else:
                    failure = root['Body']['{urn:oasis:names:tc:SAML:1.0:protocol}Response']['Status'][
                        'StatusMessage'].text
            except AttributeError:
                failure = True

            if failure:
                # Validation failed - ABORT
                msg = 'Validation of ticket {0} failed with message: {1}'.format(ticket, failure)
                log.debug(msg)
                if cas_plugin.REDIRECT_ON_UNSUCCESSFUL_LOGIN:
                    redirect(cas_plugin.REDIRECT_ON_UNSUCCESSFUL_LOGIN)
                abort(401, msg)

            log.debug('Validation of ticket {0} succeeded.'.format(ticket))
            username = data_dict['user']
            email = data_dict['email']
            fullname = data_dict['fullname']
            sysadmin = data_dict['sysadmin']
            username = self._authenticate_user(username, email, fullname, sysadmin)

            insert_entry(ticket, username)
            redirect(t.h.url_for(controller='user', action='dashboard', id=username))

        else:
            msg = 'MethodNotSupported: {0}'.format(t.request.method)
            log.debug(msg)
            abort(405, msg)

    def _authenticate_user(self, username, email, fullname, is_superuser):
        user = m.User.get(username)

        if not is_superuser or is_superuser == 'False':
            is_superuser = False
        else:
            is_superuser = True

        if user is None:
            data_dict = {'name': unicode(username),
                         'email': email,
                         'fullname': fullname,
                         'password': uuid4().hex}
            try:
                user_obj = l.get_action('user_create')({'ignore_auth': True}, data_dict)
            except Exception as e:
                log.error(e)
                abort(500, str(e))

            if is_superuser:
                try:
                    user_obj.update({'sysadmin': True})
                    l.get_action('user_update')({'ignore_auth': True}, user_obj)
                except Exception as e:
                    log.error(e)

            set_repoze_user(user_obj['name'])
            delete_user_entry(user_obj['name'])
            return user_obj['name']
        else:
            try:
                user_obj = {'id': username,
                            'email': email,
                            'fullname': fullname,
                            'sysadmin': is_superuser}
                l.get_action('user_update')({'ignore_auth': True}, user_obj)
            except Exception as e:
                log.error(e)
                abort(500, str(e))

            set_repoze_user(username)
            delete_user_entry(username)
            return username

    def cas_callback(self, **kwargs):
        log.debug('Invoked "cas_callback" method.')
        cas_plugin = p.get_plugin('cas')
        if t.request.method.lower() == 'get':
            ticket = t.request.params.get(cas_plugin.TICKET_KEY)
            if not ticket:
                t.response.set_cookie(cas_plugin.LOGIN_CHECKUP_COOKIE, str(time.time()),
                                      max_age=cas_plugin.LOGIN_CHECKUP_TIME)
                next_url = t.request.params.get('next', '/')
                redirect(cas_plugin.CAS_APP_URL + next_url)

            log.debug('Validating ticket: {0}'.format(ticket))
            q = rq.get(cas_plugin.SERVICE_VALIDATION_URL,
                       params={cas_plugin.TICKET_KEY: ticket,
                               cas_plugin.SERVICE_KEY: cas_plugin.CAS_APP_URL + '/cas/callback'})

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
                msg = 'Validation of ticket {0} failed with message: {1}'.format(ticket, failure)
                log.debug(msg)
                if cas_plugin.REDIRECT_ON_UNSUCCESSFUL_LOGIN:
                    redirect(cas_plugin.REDIRECT_ON_UNSUCCESSFUL_LOGIN)
                abort(401, msg)

            log.debug('Validation of ticket {0} succedded. Authenticated user: {1}'.format(ticket, username.text))
            attrs = root.authenticationSuccess.attributes.__dict__
            data_dict = {}
            for key, val in cas_plugin.USER_ATTR_MAP.items():
                if type(val) == list:
                    data_dict[key] = ' '.join([attrs.get(x).text for x in val])
                else:
                    data_dict[key] = attrs.get(val).text

            fullname = data_dict['fullname']
            email = data_dict['email']
            sysadmin = data_dict['sysadmin'] or None
            username = data_dict['user']

            username = self._authenticate_user(username, email, fullname, sysadmin)
            insert_entry(ticket, username)
            redirect(t.h.url_for(controller='user', action='dashboard', id=username))

        else:
            msg = 'MethodNotSupported: {0}'.format(t.request.method)
            log.debug(msg)
            abort(405, msg)
