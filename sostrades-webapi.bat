SET FLASK_APP=sos_trades_api/base_server.py
SET FLASK_ENV=production
SET SOS_TRADES_SERVER_CONFIGURATION=C:\Users\NG871FD\work\SOS_TRADES\SOURCES\infrastructure\local_configuration\configuration\development_configuration.json
SET SOS_TRADES_REFERENCES=C:\Temp\SoSTrades_persistance\reference
SET SOS_TRADES_DATA=C:\Temp\SoSTrades_persistance
SET EEB_PATH=C:\Temp\SoSTrades_persistance\eeb.yaml
SET SOS_TRADES_RSA=C:\Temp\SoSTrades_persistance\rsa
SET SQL_ACCOUNT=sostrades
SET SQL_PASSWORD=sostrades
SET LOG_USER=sostrades_log
SET LOG_PASSWORD=sostrades_log
SET "SECRET_KEY=t0)&s2!!aq4@08v5!jw&v_#!9yapq7amsm59&j*z+lsniwa_)d"
SET SAML_V2_METADATA_FOLDER=C:\Users\NG871FD\work\SOS_TRADES\SOURCES\infrastructure\CorpSSO\production

SET SOS_TRADES_EXECUTION_STRATEGY=subprocess


REM flask db upgrade
REM flask init_process

START "" waitress-serve --listen=0.0.0.0:5003 sos_trades_api.post_processing_server:app
START "" waitress-serve --listen=0.0.0.0:5001 sos_trades_api.data_server:app
START "" waitress-serve --listen=0.0.0.0:5000 sos_trades_api.main_server:app
START "" waitress-serve --listen=0.0.0.0:5004 sos_trades_api.api_v0_server:app