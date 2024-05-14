import sqlite3
from time import strftime, localtime
from logging import Handler, _defaultFormatter
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

    def __init__(self, db):
        """
        Constructor
        @param db: path to SQLite database file
        """
        Handler.__init__(self)
        self.db = db

        # Create table if not exists
        conn = sqlite3.connect(self.db)
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
            conn = sqlite3.connect(self.db)
            cursor = conn.cursor()
            cursor.execute(ApplicationSQLiteHandler.insertion_sql, data)
            conn.commit()
        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            if conn:
                conn.close()
