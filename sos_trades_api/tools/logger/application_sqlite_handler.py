
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
import sqlite3
from logging import Handler, _defaultFormatter
from time import localtime, strftime

from flask import has_request_context, request

TIME_FMT = '%Y-%m-%d %H:%M:%S'


class ApplicationSQLiteHandler(Handler):
    """
    Logging handler for SQLite.
    """

    initial_sql = """CREATE TABLE IF NOT EXISTS log(
                        Id INTEGER PRIMARY KEY,
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """

    def __init__(self, SQLITE_DATABASE):
        """
        Constructor
        @param SQLITE_DATABASE: path to SQLite database file
        """
        Handler.__init__(self)
        self.database_file = SQLITE_DATABASE

        # Create table if not exists
        conn = sqlite3.connect(self.database_file)
        cursor = conn.cursor()
        cursor.execute(ApplicationSQLiteHandler.initial_sql)
        conn.commit()
        conn.close()

    def format_db_time(self, record):
        """
        Time formatter
        @param record: Logger handler record
        """
        record.dbtime = strftime(TIME_FMT, localtime(record.created))

    def emit(self, record):
        """
        Execute SQL request to insert log record into SQLite database.
        @param record:
        """
        if has_request_context():
            record.url = request.url

        self.format(record)
        self.format_db_time(record)
        if record.exc_info:
            record.exc_text = _defaultFormatter.formatException(
                record.exc_info)
        else:
            record.exc_text = ""

        # Prepare data for insertion
        data = (record.dbtime, record.name, record.levelno, record.levelname,
                record.msg, record.exc_text, record.user, record.remoteaddr,
                record.remoteport, record.useragent)

        try:
            conn = sqlite3.connect(self.database_file)
            cursor = conn.cursor()
            cursor.execute(ApplicationSQLiteHandler.insertion_sql, data)
            conn.commit()
        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            if conn:
                conn.close()

    @classmethod
    def validate_config_dict(cls, config_dict) -> dict:
        """
        Validate configuration dictionary and returns the config dict expected
        """
        return {
            "SQLITE_DATABASE": config_dict.get("SQLITE_DATABASE")
        }
