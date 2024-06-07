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

from flask import jsonify, make_response, request, session
from werkzeug.exceptions import BadRequest

from sos_trades_api.controllers.sostrades_data.news_controller import (
    create_news,
    delete_news,
    get_news,
    update_news,
)
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.authentication.authentication import auth_required
from sos_trades_api.tools.right_management.access_right import check_user_is_manager


@app.route('/api/data/news', methods=['GET'])
@auth_required
def get_all_news():
    """
    Retrieve all news information about application
    :return: all new_information[]
    """

    news = get_news()
    resp = make_response(jsonify(news), 200)
    return resp


@app.route('/api/data/news', methods=['POST'])
@auth_required
def create_new_news():
    """
    Create a news in database
    """

    user = session['user']
    message = request.json.get('message', None)

    if message is None:
        raise BadRequest('Missing mandatory parameter: message')

    # Check if user profile is manager
    is_manager = check_user_is_manager(user.user_profile_id)

    if is_manager:
        resp = make_response(jsonify(create_news(message, user.id)), 200)
        return resp

    else:
        raise BadRequest('You do not have the necessary rights to create a news')


@app.route('/api/data/news/<int:news_identifier>', methods=['POST'])
@auth_required
def update_message_by_id(news_identifier):
    """
    Update a specific news in database
    :param news_identifier: news identifier to retrieve
    """

    user = session['user']

    if news_identifier is None or news_identifier <= 0:
        raise BadRequest(
            'Invalid argument value for news_identifier.')

    message = request.json.get('message', None)

    if message is None:
        raise BadRequest('Missing mandatory parameter: message')

    # Check if user profile is manager
    is_manager = check_user_is_manager(user.user_profile_id)
    if is_manager:
        resp = make_response(jsonify(update_news(message, news_identifier)), 200)
        return resp
    else:
        raise BadRequest('You do not have the necessary rights to update a news')


@app.route('/api/data/news/<int:news_identifier>', methods=['DELETE'])
@auth_required
def delete_message_by_id(news_identifier):
    """
       Delete a specific message in database
       :param news_identifier: message identifier to retrieve
       """
    user = session['user']

    if news_identifier is None or news_identifier <= 0:
        raise BadRequest(
            'Invalid argument value for news_identifier.')

    # Check if user profile is manager
    is_manager = check_user_is_manager(user.user_profile_id)

    if is_manager:
        delete_news(news_identifier)
        resp = make_response("", 204)
        return resp

    else:
        raise BadRequest('You do not have the necessary rights to delete a news')



