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

from logging import Handler, LogRecord, _defaultFormatter
from time import localtime, strftime

from flask import has_request_context, request
from sqlalchemy import Column, Integer, Sequence, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

TIME_FMT = "%Y-%m-%d %H:%M:%S"

Base = declarative_base()

class Log(Base):
    __tablename__ = 'log'
    Id = Column(Integer, Sequence('log_id_seq'), primary_key=True)
    Created = Column(Text)
    Name = Column(Text)
    LogLevel = Column(Integer)
    LogLevelName = Column(Text)
    Message = Column(Text)
    Exception = Column(Text)
    User = Column(Text)
    RemoteAddr = Column(Text)
    RemotePort = Column(Text)
    UserAgent = Column(Text)


class ApplicationSQLAlchemyHandler(Handler):
    """
    Logging handler for MySQL using SQLAlchemy.

    This handler writes log records to a MySQL database using SQLAlchemy.
    """

    def __init__(self, connection_string:str, connect_args:dict, engine_options:dict):
        """
        Initialize the handler with the database connection details.

        Args:
            connection_string (str): The database connection URL.
            connect_args (dict): Additional arguments to be passed to the database engine.
            engine_options (dict): Additional arguments to be passed when creating engine.
        """
        super().__init__()

        self.engine = create_engine(url=connection_string, connect_args=connect_args, **engine_options)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def format_db_time(self, record:LogRecord):
        """
        Format the log record's creation time for the database.

        Args:
            record (LogRecord): The log record.
        """
        record.dbtime = strftime(TIME_FMT, localtime(record.created))

    def emit(self, record:LogRecord):
        """
        Write a log record to the database.

        Args:
            record (LogRecord): The log record.
        """
        if has_request_context():
            record.url = request.url

        message = self.format(record)
        self.format_db_time(record)
        record.exc_text = _defaultFormatter.formatException(record.exc_info) if record.exc_info else ""

        try:
            # Instanciate msg with argument format
            if "%" in record.msg:
                record.msg = record.msg % record.args
        except:
            pass

        session = self.Session()
        try:
            log_entry = Log(
                Created=record.dbtime,
                Name=record.name,
                LogLevel=record.levelno,
                LogLevelName=record.levelname,
                Message=message,
                Exception=record.exc_text,
                User=getattr(record, 'user', ''),
                RemoteAddr=getattr(record, 'remoteaddr', ''),
                RemotePort=getattr(record, 'remoteport', ''),
                UserAgent=getattr(record, 'useragent', '')
            )
            session.add(log_entry)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
