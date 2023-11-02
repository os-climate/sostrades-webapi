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
from flask_socketio import emit, join_room, leave_room
from sos_trades_api.server.message_server import socketio
from sos_trades_api.tools.authentication.authentication import auth_refresh_required, get_authenticated_user
from sos_trades_api.tools.coedition.coedition import UserCoeditionAction, CoeditionMessage, \
    add_user_to_room, get_user_list_in_room, remove_user_from_room, remove_user_from_all_rooms, \
    add_notification_db


@socketio.on('connect')
@auth_refresh_required
def connect():
    user = get_authenticated_user()
    remove_user_from_all_rooms(user.id)
    #emit('connect', {'message': f'{user.username} has joined'})


@socketio.on('disconnect')
@auth_refresh_required
def disconnect():
    user = get_authenticated_user()
    remove_user_from_all_rooms(user.id)
    emit('disconnect', {
        'message': f'{user.username} has left'})


@socketio.on('join')
@auth_refresh_required
def on_join(data):
    room = data['study_case_id']
    user = get_authenticated_user()
    remove_user_from_all_rooms(user.id)
    add_user_to_room(user.id, data['study_case_id'])
    join_room(room)
    users = get_user_list_in_room(data['study_case_id'])

    # Add notification to database
    add_notification_db(data['study_case_id'], user,
                        UserCoeditionAction.JOIN_ROOM)

    # Emit notification
    emit('room-user-update',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.JOIN_ROOM,
          'message': CoeditionMessage.JOIN_ROOM,
          'users': users},
         room=room)


@socketio.on('leave')
@auth_refresh_required
def on_leave(data):
    room = data['study_case_id']
    user = get_authenticated_user()
    remove_user_from_room(user.id, data['study_case_id'])
    leave_room(room)
    users = get_user_list_in_room(data['study_case_id'])

    # Add notification to database
    add_notification_db(data['study_case_id'], user,
                        UserCoeditionAction.LEAVE_ROOM)

    # Emit notification
    emit('room-user-update',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.LEAVE_ROOM,
          'message': CoeditionMessage.LEAVE_ROOM,
          'users': users},
         room=room)


@socketio.on('save')
@auth_refresh_required
def on_save(data):
    room = data['study_case_id']
    changes = data['changes']
    user = get_authenticated_user()

    # Emit notification
    emit('study-saved',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.SAVE,
          'changes': changes,
          'message': CoeditionMessage.SAVE},
         room=room)


@socketio.on('reload')
@auth_refresh_required
def on_reload(data):
    room = data['study_case_id']
    user = get_authenticated_user()

    # Emit notification
    emit('study-reloaded',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.RELOAD,
          'message': CoeditionMessage.RELOAD},
         room=room)


@socketio.on('submit')
@auth_refresh_required
def on_submit(data):
    room = data['study_case_id']
    user = get_authenticated_user()

    # Add notification to database
    add_notification_db(data['study_case_id'], user,
                        UserCoeditionAction.SUBMISSION)

    # Emit notification
    emit('study-submitted',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.SUBMISSION,
          'message': CoeditionMessage.SUBMISSION},
         room=room)


@socketio.on('execute')
@auth_refresh_required
def on_execute(data):
    room = data['study_case_id']
    submitted = data['submitted']
    user = get_authenticated_user()

    # Add notification to database
    add_notification_db(data['study_case_id'], user,
                        UserCoeditionAction.EXECUTION)

    # Emit notification
    emit('study-executed',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.EXECUTION,
          'message': CoeditionMessage.EXECUTION,
          'submitted': submitted},
         room=room)


@socketio.on('claim')
@auth_refresh_required
def on_claim(data):
    room = data['study_case_id']
    user = get_authenticated_user()

    # Add notification to database
    add_notification_db(data['study_case_id'], user,
                        UserCoeditionAction.CLAIM)

    # Emit notification
    emit('study-claimed',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.CLAIM,
          'message': CoeditionMessage.CLAIM,
          'user_id_execution_authorized': user.id},
         room=room)


@socketio.on('delete')
@auth_refresh_required
def on_delete(data):
    room = data['study_case_id']
    user = get_authenticated_user()

    # Emit notification
    emit('study-deleted',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.DELETE},
         room=room)


@socketio.on('edit')
@auth_refresh_required
def on_edit(data):
    room = data['study_case_id']
    user = get_authenticated_user()

    # Emit notification
    emit('study-edited',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.EDIT},
         room=room)


@socketio.on('validation-change')
@auth_refresh_required
def on_validation_change(data):
    room = data['study_case_id']
    user = get_authenticated_user()
    treenode = data['treenode_data_name']
    validation = data['validation_state']

    # Add notification to database
    add_notification_db(data['study_case_id'], user,
                        UserCoeditionAction.VALIDATION_CHANGE)
    # Emit notification
    emit('validation-change',
         {'author': f'{user.firstname} {user.lastname}',
          'type': UserCoeditionAction.VALIDATION_CHANGE,
          'study_case_id': room,
          'message': CoeditionMessage.VALIDATION_CHANGE,
          'treenode_data_name': treenode,
          'validation_state': validation},
         room=room)


