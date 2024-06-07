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
from logging import Handler, _defaultFormatter
from time import localtime, strftime

from sos_trades_api.models.database_models import ReferenceStudyExecutionLog
from sos_trades_api.server.base_server import app, db

TIME_FMT = '%Y-%m-%d %H:%M:%S'


class ReferenceMySQLHandler(Handler):
    """
    Logging handler for StudyCaseExecutionLog
    """

    def __init__(self, reference_identifier):
        """
        Constructor
        :param reference_identifier: identifier of the associated reference
        :type reference_identifier: str
        """

        Handler.__init__(self)

        self.__reference_identifier = reference_identifier
        self.__inner_bulk_list = []

    def formatDBTime(self, record):
        """
        Time formatter
        @param record:
        @return: nothing
        """
        record.dbtime = strftime(TIME_FMT, localtime(record.created))

    def emit(self, record):
        """
        Connect to DB, execute SQL Request, disconnect from DB
        @param record:
        @return:
        """

        # Use default formatting:
        self.format(record)

        # Set the database time up:
        self.formatDBTime(record)

        if record.exc_info:
            record.exc_text = _defaultFormatter.formatException(record.exc_info)
        else:
            record.exc_text = ""

        try:
            # Instanciate msg with argument format
            if '%' in record.msg:
                record.msg = record.msg % record.args
        except:
            pass

        try:
            # Reset args to avoir manipulate tuple in database
            record.args = ''

            rel = ReferenceStudyExecutionLog()

            rel.created = record.dbtime
            rel.name = record.name
            rel.log_level_name = record.levelname
            rel.message = record.msg
            rel.exception = str(record.exc_text)
            rel.reference_id = self.__reference_identifier

            self.__inner_bulk_list.append(rel)

            self.__write_into_database()

        except Exception as e:
            print(e)

    def flush(self):
        """Flush remaining message"""
        self.__write_into_database(True)

    def clear_reference_database_logs(self):
        """
        Clear reference log from database
        """
        try:
            with app.app_context():
                db.session.query(ReferenceStudyExecutionLog).filter(
                    ReferenceStudyExecutionLog.reference_id
                    == self.__reference_identifier
                ).delete()
                db.session.commit()
        except Exception as ex:
            print(f'Reference mysql handler: {str(ex)}')

    def __write_into_database(self, flush=False):
        """Write stored object into database

        :params: flush, boolean to flush the list without taking into account number of elements
        :type: boolean
        """
        if len(self.__inner_bulk_list) > 200 or flush == True:
            try:
                with app.app_context():
                    db.session.bulk_save_objects(self.__inner_bulk_list)
                    db.session.commit()
            except Exception as ex:
                print(f'Reference mysql handler: {str(ex)}')
            self.__inner_bulk_list = []
