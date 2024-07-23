'''
Copyright 2022 Airbus SAS
Modifications on 23/07/2024 Copyright 2024 Capgemini

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

import time
from datetime import datetime
from logging import Handler, _defaultFormatter

from sos_trades_api.models.database_models import StudyCaseLog
from sos_trades_api.server.base_server import app, db

TIME_FMT = "%Y-%m-%d %H:%M:%S"


class StudyCaseSQLAlchemyHandler(Handler):
    """
    Logging handler for StudyCaseLog
    """

    def __init__(self, study_case_id, bulk_transaction=False):
        """
        Constructor
        :param study_case_id: identifier of the associated study case
        :type study_case_id: integer

        :param bulk_transaction: boolean that enable or not record management by bulk regarding the database
                Activate bulk transaction improve performance regarding calculation but it is necessary
                to flush data calling flush method at the end of the process
        :type bulk_transaction: boolean
        """
        Handler.__init__(self)

        self.study_case_id = study_case_id

        self.__inner_bulk_list = []
        self.__time = None
        self.__bulk_transaction = bulk_transaction

    @property
    def bulk_transaction(self):
        """
        Return a boolean indicating if the database transaction on commit is bulk or not

        @return boolean
        """
        return self.__bulk_transaction

    @bulk_transaction.setter
    def bulk_transaction(self, value):
        """
        Set a boolean indicating if the database transaction on commit is bulk or not
        Activate bulk transaction improve performance regarding calculation
        but it is necessary to flush data calling flush method at the end of the process

        :param value: enable or not bulk transaction
        :type value: boolean
        """
        self.__bulk_transaction = value

    def emit(self, record):
        """
        Connect to DB, execute SQL Request, disconnect from DB

        :param record: Logger handler record
        :type record: logger record object instance
        """
        # Use default formatting:
        self.format(record)

        # Set the database time up:
        StudyCaseSQLAlchemyHandler.format_db_time(record)

        if record.exc_info:
            record.exc_text = _defaultFormatter.formatException(
                record.exc_info)
        else:
            record.exc_text = ""

        try:
            # Check if message smth other than a string
            # An exception can occur using logger.exception(...)
            if not isinstance(record.msg, str):
                record.msg = str(record.msg)

            # Instantiate msg with argument format
            if "%" in record.msg:
                record.msg = record.msg % record.args

        except:
            pass

        try:
            # Write only not empty message
            if len(record.msg) > 0:
                # Reset args to avoid manipulate tuple in database
                record.args = ""

                # Remove study case id from record name if exist
                if f"{self.study_case_id}." in record.name:
                    record.name = record.name.replace(
                        f"{self.study_case_id}.", "")
                elif f"{self.study_case_id}" in record.name:
                    record.name = record.name.replace(
                        f"{self.study_case_id}", "")

                study_case_log = StudyCaseLog()

                study_case_log.created = record.dbtime
                study_case_log.name = record.name
                study_case_log.log_level_name = record.levelname
                study_case_log.message = record.msg
                study_case_log.exception = str(record.exc_text)
                study_case_log.study_case_id = self.study_case_id

                self.__inner_bulk_list.append(study_case_log)
                if self.bulk_transaction:
                    self.__write_bulk_into_database()
                else:
                    self.flush()
        except Exception as e:
            print(e)

    def flush(self):
        """
        Flush remaining message
        """
        self.__write_bulk_into_database(True)

    def __write_bulk_into_database(self, flush=False):
        """
        Write stored object into database

        :param flush: boolean to flush the list without taking into account number of elements
        :type flush: boolean
        """
        elapsed_time = 0

        if self.__time is None:
            self.__time = time.time()
        else:
            elapsed_time = time.time() - self.__time

        if elapsed_time > 2.0 or flush is True:
            self.__time = None
            try:
                with app.app_context():
                    db.session.bulk_save_objects(self.__inner_bulk_list)
                    db.session.commit()
            except Exception as ex:
                print(f"Study case SQLAlchemy handler: {ex!s}")
            self.__inner_bulk_list = []

    @staticmethod
    def format_db_time(record):
        """
        Time formatter
        @param record:
        @return: nothing
        """
        record.dbtime = datetime.fromtimestamp(record.created)
