import json
import logging
import requests as rq
import SimpleHTTPServer
import SocketServer

from uuid import uuid4
from threading import Thread
from urllib import unquote_plus

PORT = 8899

log = logging.getLogger(__name__)


class MockCASServer(SimpleHTTPServer.SimpleHTTPRequestHandler):
    SESSION = {}
    TICKETS = {}

    def do_GET(self):
        if 'login' in self.path:
            if 'sessionid' in self.headers and \
                            self.headers['sessionid'] in self.SESSION.keys():
                print 'USER IS ALREADY LOGGED IN'
            else:
                print 'USER IS NOT LOGGED IN DO LOGIN'
            self.respond(content='{"status": "ok"}')

        elif 'logout' in self.path:
            # Handle logout
            pass
        elif 'validate' in self.path:
            # Handle validation - CAS 1.0
            pass
        elif 'serviceValidate' in self.path:
            # Handle validation - CAS 2.0
            sessionid = self.headers.get('sessionid', None)
            if sessionid is None:
                print 'Aborting service validation. No user is logged in.'
            # TODO: Process ticket
        elif 'samlValidate' in self.path:
            # SAML Validation - CAS 3.0
            pass

    def _generate_session(self, user):
        _session = uuid4().hex
        self.SESSION[_session] = USERS.get(user)
        return _session

    def _update_session(self, sessionid, data_dict):
        self.SESSION[sessionid].update(data_dict)

    def do_POST(self):
        if 'login' in self.path:
            data = self.rfile.read(int(self.headers['Content-Length']))
            data = json.loads(data)

            if 'username' not in data or 'password' not in data:
                print 'ERROR MISSING USER AND PASS'

            user = USERS.get(data['username'], None)
            if user is None or user['password'] != data['password']:
                print 'failed user validation not setting session'

            print 'FOUND USER ', user
            sessionid = self._generate_session(user['username'])

            # Send ticket to each service
            for service in SERVICES:
                ticket = '{0}-{1}'.format(sessionid, uuid4().hex)
                self.TICKETS.update({ticket: {'used': False, 'session': sessionid}})
                url = '{0}?ticket={1}'.format(service['CALLBACK'], ticket)
                try:
                    rq.get(unquote_plus(url))
                except Exception as e:
                    log.error('Unable to reach service callback url: {0}'.format(url))
                    log.error(e)

            self.respond(content='{"status": "ok"}', headers={'sessionid': sessionid})

        elif 'logout' in self.path:
            # Handle logout
            pass
        elif 'validate' in self.path:
            # Validation CAS 1.0
            pass
        elif 'serviceValidate' in self.path:
            # Service validation CAS 2.0
            pass
        elif 'samlValidate' in self.path:
            # SAML Validation CAS 3.0
            pass

    def respond_action(self, result_dict, status=200):
        response_dict = {'result': result_dict, 'success': True}
        return self.respond_json(response_dict, status=status)

    def respond_json(self, content_dict, status=200):
        return self.respond(json.dumps(content_dict), status=status,
                            content_type='application/json')

    def respond(self, content, status=200, content_type='application/json', headers={}):
        # Set response status code
        self.send_response(status)

        # Set response headers
        self.send_header('Content-Type', content_type)
        if any(headers):
            for key, val in headers.items():
                self.send_header(key, val)
        self.end_headers()

        # Set response content
        self.wfile.write(content)
        self.wfile.close()


def serve(port=PORT):
    class TestServer(SocketServer.TCPServer):
        allow_reuse_address = True

    httpd = TestServer(("", PORT), MockCASServer)
    log.info('Serving test CAS server at port {0}'.format(PORT))
    httpd_thread = Thread(target=httpd.serve_forever)
    httpd_thread.setDaemon(True)
    httpd_thread.start()


USERS = {
    'admin': {
        'username': 'admin',
        'fullname': 'Admin User',
        'email': 'admin@local.host',
        'password': '1234',
        'is_superuser': True
    },
    'test': {
        'username': 'test',
        'fullname': 'Test User',
        'email': 'test@local.host',
        'password': '1234',
        'is_superuser': False
    }
}

SERVICES = [
    {
        'URL': 'http://localhost:5000',
        'CALLBACK': 'http://localhost:5000/cas/callback'
    }
]
