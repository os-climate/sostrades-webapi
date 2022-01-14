'''
Copyright 2022 Airbus SAS

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
"""
mode: python; py-indent-offset: 4; tab-width: 4; coding: utf-8
SMTP service
"""

# pylint: disable=line-too-long
import smtplib
from smtplib import SMTPException
from email.message import EmailMessage
from sos_trades_api.base_server import app


def send_new_user_mail(user):
    """ Methods notifying using an automatic mail that a new user has
    connected to the application

    :params: user instance
    :type: User
    """

    message = EmailMessage()
    message['Subject'] = f'New user connected to Sos Trades : {user.firstname},{user.lastname}'
    message['From'] = app.config['SMTP_SOS_TRADES_ADDR']
    message['To'] = app.config['SMTP_SOS_TRADES_ADDR']
    message.set_content('SoS Trades new user message.')
    message.add_alternative("""\
    <!DOCTYPE html>
        <html>
            <body>

                <h3 style="margin-bottom:10px">A new user just connected to SoS Trades Application</h3>
                 <table border="1" >
                  <tr>
                    <th style="padding:10px">Username</th>
                    <th style="padding:10px">First name</th>
                    <th style="padding:10px">Last name</th>
                    <th style="padding:10px">Email</th>
                    <th style="padding:10px">Environment</th>
                  </tr>
                  <tr>
                    <td style="padding:10px">%s</td>
                    <td style="padding:10px">%s</td>
                    <td style="padding:10px">%s</td>
                    <td style="padding:10px">%s</td>
                    <td style="padding:10px">%s</td>
                  </tr>
                </table> 
        
            </body>
        </html>
    """ % (user.username, user.firstname, user.lastname, user.email, app.config['SOS_TRADES_ENVIRONMENT']), subtype='html')

    try:
        smtp_obj = smtplib.SMTP(app.config['SMTP_SERVER'])
        smtp_obj.send_message(message)
        return True
    except SMTPException:
        return False


def send_right_update_mail(user, profilename):
    """ Methods notifying a user when its profile is changed in the application

    :params: user instance
    :type: User

    :params: user new profile name
    :type: str
    """

    message = EmailMessage()
    message['Subject'] = f'SoSTrades authorization rights updated'
    message['From'] = app.config['SMTP_SOS_TRADES_ADDR']
    message['To'] = user.email
    message.set_content(
        'The authorization rights for your account have been updated.')
    message.add_alternative("""\
    <!DOCTYPE html>
        <html>
            <body>
                <h3 style="margin-bottom:10px">The authorization rights for your account have been updated.</h3>
                <p>
                A new profile has been applied to your account : <span style="color:green">%s</span>
                </p>
                 <p>
                Please log in again to SoSTrades Application.
                </p>
                <b>SoSTrades Team</b>
            </body>
        </html>
    """ % (profilename), subtype='html')

    try:
        smtp_obj = smtplib.SMTP(app.config['SMTP_SERVER'])
        smtp_obj.send_message(message)
        return True
    except SMTPException:
        return False


def send_password_reset_mail(user, reset_link):
    """ Methods notifying a user when its profile is changed in the application

    :param user instance
    :type User

    :param reset_link, link to password reset page
    :type str
    """

    message = EmailMessage()
    message['Subject'] = f'SoSTrades password reset request'
    message['From'] = app.config['SMTP_SOS_TRADES_ADDR']
    message['To'] = user.email
    message.set_content(f'''\
        Reset password request has been taken into account. 
        Use the link below to change your password
        {reset_link}
        ''')
    message.add_alternative(f'''\
    <!DOCTYPE html>
        <html>
            <body>
                <h3 style="margin-bottom:10px">Reset password request has been taken into account.</h3>
                <p>
                Use the link below to change your password
                </p>
                 <p>
                {reset_link}
                </p>
                <b>SoSTrades Team</b>
            </body>
        </html>
    ''')

    try:
        smtp_obj = smtplib.SMTP(app.config['SMTP_SERVER'])
        smtp_obj.send_message(message)
        return True
    except SMTPException as ex:
        print(ex)
        return False
