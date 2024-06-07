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
import queue
import threading
import time
from copy import deepcopy

from sostrades_core.execution_engine.sos_mdo_discipline import SoSMDODiscipline

from sos_trades_api.models.database_models import StudyCaseDisciplineStatus
from sos_trades_api.server.base_server import app, db

"""
Execution engine observer
"""

class ExecutionEngineObserver():
    """Class that manage observer process implemented into discipline in order to be notified
    on each execution status changes and to store this change in the database for further treatment using the API
    """

    def __init__(self, study_case_id):
        """Constructor

        :param study_case_id: study case identifier in database (integer) use to 
            identified the discipline to update in database
        """
        self.__study_case_id = study_case_id
        self.__queue = queue.Queue()
        self.__started = True
        self.__stop_code = 'THREAD_STOP'
        self.__status_changes = {}
        self.__timer = None
        self.__identifier_mapping = {}

        self.__thread = threading.Thread(target=self.__update_database)
        self.__thread.start()

    def stop(self):
        """ Methods the stop the current thread
        """
        self.__started = False
        self.__queue.put(self.__stop_code)
        self.__thread.join()
        self.__status_changes = {}

    def set_object_mapping_id(self, identifier_mapping):
        """ Give the correspondance between database primary ley and associated discipline key in order
        to speed-up update operation
        """

        self.__identifier_mapping = deepcopy(identifier_mapping)

    def update_status(self, discipline):
        """ Methods to implement in order to be notified for a status change during discipline
        execution
        """
        # Send a status to update into the queue
        if isinstance(discipline, SoSMDODiscipline):

            # Send update to the queue
            self.__queue.put([discipline.name, discipline.status])

    def __update_database(self):
        """ Threaded methods to update the database without blocking execution process
        A queue system is used in order to populate the data to update and keeping alive the database connection
        for better performance
        """
        mappings_data = []
        flush = False
        initial_time = None
        elasped_time = 0
        disciplines_entries = {}

        # Infinite loop with queue system
        # The database connection is kept open
        while self.__started:

            infos = self.__queue.get()

            # First timer initialisation
            if initial_time is None:
                initial_time = time.time()
                elasped_time = 0
            else:
                elasped_time = time.time() - initial_time

            if infos == self.__stop_code:
                # flush pending changes
                flush = True
            else:
                discipline_identifier = infos[0]
                discipline_status = infos[1]

                if discipline_identifier in self.__identifier_mapping:
                    disciplines_entries[self.__identifier_mapping[discipline_identifier]
                                        ] = discipline_status

            if elasped_time > 2.0 or flush == True:
                if len(disciplines_entries) > 0:

                    for discipline_identifier, discipline_status in disciplines_entries.items():
                        mappings_data.append(
                            {
                                'id': discipline_identifier,
                                'status': discipline_status
                            })

                    disciplines_entries = {}

                    # Add an exception manager to ensure that database eoor will not
                    # shut down calculation
                    try:
                        # Open a database context
                        with app.app_context():
                            db.session.bulk_update_mappings(
                                StudyCaseDisciplineStatus, mappings_data)
                            db.session.commit()
                    except Exception as ex:
                        print(f'Execution engine observer: {str(ex)}')

                    mappings_data = []
                initial_time = None
                flush = False

            self.__queue.task_done()
