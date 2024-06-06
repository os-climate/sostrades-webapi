
'''
Copyright 2024 Capgemini

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
import logging
from sos_trades_api.tools.authentication.authentication import get_authenticated_user
from flask import has_request_context, request

class ApplicationRequestFormatter(logging.Formatter):
    def format(self, record):

        record.user = ''
        record.remoteaddr = ''
        record.remoteport = ''
        record.useragent = ''

        if has_request_context():

            try:
                user = get_authenticated_user()
                record.user = user.email
            except:
                pass

            # DEBUG LINES TO CHECK HEADERS CONTENT
#             print('HEADERS')
#             for key in request.headers:
#                 print(f'{key} => {request.headers.get(key)}')
#
#             print('ENVIRON')
#             for key in request.environ:
#                 print(f'{key} => {request.environ.get(key)}')

            if 'X-Forwarded-Host' in request.headers:
                # A proxy is used, so get the origin client address
                record.remoteaddr = request.headers.get('X-Forwarded-Host')
            else:
                # Retrieve standard remote address from request
                record.remoteaddr = request.environ.get('REMOTE_ADDR')

            record.useragent = request.environ.get('HTTP_USER_AGENT')

        return super().format(record)