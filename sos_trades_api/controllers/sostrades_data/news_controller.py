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
import traceback
from datetime import datetime, timezone

from sos_trades_api.models.database_models import News
from sos_trades_api.server.base_server import db


class NewsError(Exception):
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


class InvalidNews(NewsError):
    """Invalid news"""


def get_news():
    """
    Ask database to retrieve all news

    :returns: sos_trades_api.models.database_models.News[]
    """

    all_news = News.query.order_by(
        News.last_modification_date.desc()
    ).all()

    return all_news


def create_news(message, user_identifier):
    """
    Create a news in database
    :param message: message to add into database
    :param user_identifier: User that create this news
    :return: sos_trades_api.models.database_models.News
    """
    
    if len(message) <= 300:
        new_post = News()
        new_post.message = message
        new_post.user_id = user_identifier

        db.session.add(new_post)
        db.session.commit()

        return new_post
    else:
        raise InvalidNews("The length of the message is greater than 300 characters")


def update_news(new_message, news_identifier):
    """
    Update an existing news in database
    :param news_identifier: news object to update
    :param new_message: message to update
    :return: sos_trades_api.models.database_models.News
    """

    # First check that this link does already exist in database
    existing_message = News.query.filter(News.id == news_identifier).first()

    if existing_message is None:
        raise InvalidNews('News to update not found.')

    if len(new_message) <= 300:
        existing_message.message = new_message
        existing_message.last_modification_date = datetime.now().astimezone(timezone.utc).replace(tzinfo=None)

        db.session.add(existing_message)
        db.session.commit()

        return existing_message
    else:
        raise InvalidNews("The length of the message is greater than 300 characters")


def delete_news(news_identifier):
    """
    Delete the news specified by its identifier given as parameter
    :param news_identifier: news_identifier to delete
    """

    # First check that this news does already exist in database
    existing_message = News.query.filter(News.id == news_identifier).first()

    if existing_message is None:
        raise InvalidNews('News to delete not found.')

    db.session.delete(existing_message)
    db.session.commit()
