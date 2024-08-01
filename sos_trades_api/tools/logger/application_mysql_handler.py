'''
Copyright 2022 Airbus SAS
Modifications on 2024/06/07-2024/08/01 Copyright 2024 Capgemini
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
from logging import Handler, _defaultFormatter
from re import escape, findall
from time import localtime, strftime

import MySQLdb
from flask import has_request_context, request
from MySQLdb._exceptions import MySQLError
from MySQLdb._mysql import escape_string

from sos_trades_api.tools.authentication.authentication import get_authenticated_user

TIME_FMT = "%Y-%m-%d %H:%M:%S"


class ApplicationRequestFormatter(logging.Formatter):
    def format(self, record):

        record.user = ""
        record.remoteaddr = ""
        record.remoteport = ""
        record.useragent = ""

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

            if "X-Forwarded-Host" in request.headers:
                # A proxy is used, so get the origin client address
                record.remoteaddr = request.headers.get("X-Forwarded-Host")
            else:
                # Retrieve standard remote address from request
                record.remoteaddr = request.environ.get("REMOTE_ADDR")

            record.useragent = request.environ.get("HTTP_USER_AGENT")

        return super().format(record)


class ApplicationMySQLHandler(Handler):
    """
    Logging handler for MySQL.

    """

    initial_sql = """CREATE TABLE IF NOT EXISTS log(
                        Id INT AUTO_INCREMENT PRIMARY KEY,
                        Created text,
                        Name text,
                        LogLevel int,
                        LogLevelName text,
                        Message text,
                        Exception text,
                        User text,
                        RemoteAddr text,
                        RemotePort text,
                        UserAgent text
                    )"""

    insertion_sql = """INSERT INTO log(
                        Created,
                        Name,
                        LogLevel,
                        LogLevelName,
                        Message,
                        Exception,
                        User,
                        RemoteAddr,
                        RemotePort,
                        UserAgent
                    )
                    VALUES (
                        '%(dbtime)s',
                        '%(name)-20s',
                         %(levelno)d,
                        '%(levelname)-10s',
                        '%(msg)s',
                        '%(exc_text)s',
                        '%(user)s',
                        '%(remoteaddr)s',
                        '%(remoteport)s',
                        '%(useragent)s'
                    );
                    """
    sql_fields = findall(escape("%(") + "(.*)" + escape(")"), insertion_sql)

    def __init__(self, db):
        """
        Constructor
        @param db: {'HOST','PORT','USER', 'PASSWORD', 'DATABASE_NAME', 'SSL'}
        """
        Handler.__init__(self)

        self.db = db

        # Check if 'log' table in db already exists
        result = self.check_table_presence()

        # If not exists, then create the table
        if not result:
            try:
                conn = self.__get_connection()
            except MySQLError as error:
                raise Exception(error)
            else:
                cur = conn.cursor()
                try:
                    cur.execute(ApplicationMySQLHandler.initial_sql)
                except MySQLError as error:
                    conn.rollback()
                    cur.close()
                    conn.close()
                    raise Exception(error)
                else:
                    conn.commit()
                finally:
                    cur.close()
                    conn.close()

    def __get_connection(self):

        if self.db["SSL"]:
            return MySQLdb.connect(host=self.db["HOST"], port=self.db["PORT"],
                                    user=self.db["USER"], passwd=self.db["PASSWORD"], db=self.db["DATABASE_NAME"],
                                    ssl=self.db["SSL"])
        else:
            return MySQLdb.connect(host=self.db["HOST"], port=self.db["PORT"],
                                   user=self.db["USER"], passwd=self.db["PASSWORD"], db=self.db["DATABASE_NAME"])


    def check_table_presence(self):
        try:
            conn = self.__get_connection()
        except MySQLError as error:
            raise Exception(error)
        else:
            # Check if 'log' table in db already exists
            cur = conn.cursor()
            stmt = "SHOW TABLES LIKE 'log';"
            cur.execute(stmt)
            result = cur.fetchone()
            cur.close()
            conn.close()

        if not result:
            return 0
        else:
            return 1

    def format_db_time(self, record):
        """
        Time formatter
        @param record: Logger handler record

        """
        record.dbtime = strftime(TIME_FMT, localtime(record.created))

    def emit(self, record):
        """
        Connect to DB, execute SQL Request, disconnect from DB
        @param record:
        @return: 
        """
        # Inject own variables
        if has_request_context():
            record.url = request.url

        # Use default formatting:
        self.format(record)
        # Set the database time up:
        self.format_db_time(record)
        if record.exc_info:
            record.exc_text = _defaultFormatter.formatException(
                record.exc_info)
        else:
            record.exc_text = ""

        # Escape special character in string values
        for k in self.sql_fields:
            v = getattr(record, k)
            if isinstance(v, str):
                setattr(record, k, escape_string(
                    v.replace("'", "''")).decode("utf-8"))
            elif v.__class__.__name__ == "Exception":
                setattr(record, k, escape_string(str(v)).decode("utf-8"))

        try:
            # Instanciate msg with argument format
            if "%" in record.msg:
                record.msg = record.msg % record.args

            # Reset args to avoir manipulate tuple in database
            record.args = ""

            # Insert log record
            sql = ApplicationMySQLHandler.insertion_sql % record.__dict__

        except:
            sql = ""

        if len(sql) > 0:
            try:
                # Insert log record
                conn = self.__get_connection()
            except MySQLError as error:
                from pprint import pprint
                print("The Exception during db.connect")
                pprint(error)
                raise Exception(error)

            cur = conn.cursor()
            try:
                cur.execute(sql)
            except MySQLError as error:
                errno, errstr = error.args
                if not errno == 1146:
                    raise
                cur.close()  # close current cursor
                cur = conn.cursor()  # recreate it (is it mandatory?)
                try:            # try to recreate table
                    cur.execute(ApplicationMySQLHandler.initial_sql)

                except MySQLError as error:
                    # definitly can't work...
                    conn.rollback()
                    cur.close()
                    conn.close()
                    raise Exception(error)
                else:   # if recreate log table is ok
                    conn.commit()
                    cur.close()
                    cur = conn.cursor()
                    cur.execute(sql)
                    conn.commit()
                    # then Exception vanished
            else:
                conn.commit()
            finally:
                cur.close()
                conn.close()
