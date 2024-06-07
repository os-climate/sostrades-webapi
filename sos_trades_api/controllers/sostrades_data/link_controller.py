'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07 Copyright 2024 Capgemini
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
import traceback

from sos_trades_api.models.database_models import Link
from sos_trades_api.server.base_server import db

"""
User Functions
"""

class LinkError(Exception):
    """Base link Exception"""

    def __init__(self, msg=None):
        message = None
        if msg is not None:
            if isinstance(msg, Exception):
                message = f'the following exception occurs {msg}.\n{traceback.format_exc()}'
            else:
                message = msg

        Exception.__init__(self, message)

    def __str__(self):
        return self.__class__.__name__ + '(' + Exception.__str__(self) + ')'


class InvalidLink(LinkError):
    """Invalid link"""


def get_links():
    """
    Ask database to retrieve all link informations

    :returns: sos_trades_api.models.database_models.Link[]
    """

    all_links = Link.query.all()

    return all_links


def get_link(link_identifier):
    """
    Retrieve the link specified by its identifier given as parameter
    :param link_identifier: link identifier to retrieve
    :return: sos_trades_api.models.database_models.Link
    """

    link = Link.query.filter(Link.id == link_identifier).first()

    if link is None:
        raise InvalidLink('Link not found in database')

    return link


def create_link(url, label, description, user_identifier):
    """
    Create a new link in database
    :param url: url to add into database
    :param label: label value to add into database
    :param description: description value to add into database
    :param user_identifier: User that create this link
    :return: sos_trades_api.models.database_models.Link
    """

    # First check that this link does already exist in database
    link = Link.query.filter(Link.url == url).first()

    if link is not None:
        raise InvalidLink(f'Link with url {link.url} already exist in database.\nDuplicate are not permitted.')

    new_link = Link()
    new_link.url = url
    new_link.label = label
    new_link.description = description
    new_link.user_id = user_identifier

    db.session.add(new_link)
    db.session.commit()

    return new_link


def update_link(link_identifier, url, label, description, user_identifier):
    """
    Update an existing link in database
    :param link_identifier: link object to update
    :param url: url value to update
    :param label: label value to update
    :param description: description value to update
    :param user_identifier: User that create this link
    :return: sos_trades_api.models.database_models.Link
    """

    # First check that this link does already exist in database
    existing_link = Link.query.filter(Link.id == link_identifier).first()

    if existing_link is None:
        raise InvalidLink('Link not found.')

    existing_link.url = url
    existing_link.label = label
    existing_link.description = description
    existing_link.user_id = user_identifier

    db.session.add(existing_link)
    db.session.commit()

    return existing_link


def delete_link(link_identifier):
    """
    Delete the link specified by its identifier given as parameter
    :param link_identifier: link identifier to delete
    """

    # First check that this link does already exist in database
    existing_link = Link.query.filter(Link.id == link_identifier).first()

    if existing_link is None:
        raise InvalidLink('Link not found.')

    db.session.delete(existing_link)
    db.session.commit()
