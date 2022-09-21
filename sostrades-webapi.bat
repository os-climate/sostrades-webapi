SET FLASK_APP=sos_trades_api/base_server.py
SET FLASK_ENV=
SET SOS_TRADES_SERVER_CONFIGURATION=
SET SOS_TRADES_REFERENCES=
SET SOS_TRADES_DATA=
SET EEB_PATH=
SET SOS_TRADES_RSA=
SET SQL_ACCOUNT=
SET SQL_PASSWORD=
SET LOG_USER=
SET LOG_PASSWORD=
SET SECRET_KEY=
SET SAML_V2_METADATA_FOLDER=
SET SOS_TRADES_EXECUTION_STRATEGY=
SET SOS_TRADES_SERVER_MODE=


REM flask db upgrade
REM flask init_process

START "" waitress-serve --listen=0.0.0.0:5003 sos_trades_api.post_processing_server:app
START "" waitress-serve --listen=0.0.0.0:5001 sos_trades_api.data_server:app
START "" waitress-serve --listen=0.0.0.0:5000 sos_trades_api.main_server:app
REM START "" waitress-serve --listen=0.0.0.0:5004 sos_trades_api.api_v0_server:app