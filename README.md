# SoSTrades_WebAPi


## Packages installation
### Online (no vpn) install
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org 

###Python path
It is necessary to add the SoSTrades_WebAPI folder to the PYTHONPATH.

### Dependencies
SoSTrades_WebAPI needs Sos_trades_core to run, so the Sos_trades_core folder needs to be added to the PYTHONPATH 
and the Sos_trades_core package installation needs to be done.

## Database migration

Alembic (the migration framework used by Flask-Migrate) will make these schema changes in a way that does not require the database to be recreated from scratch.

To accomplish this seemingly difficult task, Alembic maintains a migration repository, which is a directory in which it stores its migration scripts. Each time a change is made to the database schema, a migration script is added to the repository with the details of the change. To apply the migrations to a database, these migration scripts are executed in the sequence they were created.

### Create the migration repository (already done)
```bash
flask db init
```

### Generate a migration

To generate a migration automatically, Alembic compares the database schema as defined by the database models, against the actual database schema currently used in the database. It then populates the migration script with the changes necessary to make the database schema match the application models

```bash
flask db migrate -m "MIGRATION MESSAGE HERE"
```

### Database Upgrade and Downgrade Workflow

#### Database upgrade

When you are ready to release the new version of the application to your production server, all you need to do is grab the updated version of your application, which will include the new migration script, and run :
 
```bash
flask db upgrade
```

Alembic will detect that the production database is not updated to the latest revision of the schema, and run all the new migration scripts that were created after the previous release


#### Database downgrade

If you need to undoes the last migration, run :

```bash
flask db downgrade
```

#### Database model creation

You need to specify a Foreign key name when you create a new model in database_models.py file.

Naming convention => fk_tableName_columnName

Example (group_id foreign key of group table column id in study case table) :
```
group_id = Column(Integer,
                  ForeignKey(f'{Group.__tablename__}.id',
                             ondelete="CASCADE",
                             name='fk_study_case_group_id'),
                  nullable=False)
```

### Database applicative commands

#### Database initialize process
To retrieve automatically all processes in the repositories of the PYTHONPATH (processes must be in a file named 'process.py'):
```bash
flask db init_process
```
All the process will be associated to the default applicative group named "SoSTrades_Dev".

#### Database create standard account
If you want to create a local standard user account:

```bash
flask db create_standard_user username email firstname lastname
```
the username, email firstname and lastname arguments should be filled with the user information.

#### Database reset user password
If you want to reset the password of a user

```bash
flask db reset_standard_user_password username
```
The username of the user will be passed in argument
The updated password will be saved in a file on the local server.

#### Database rename the default applicative group
If you want to rename the Sostrades applicative group named "SoSTrades_Dev" by default

```bash
flask db rename_applicative_group new_name
```
The new name of the applicative group will be passed in argument

#### User profile changes
If you want to change the profile of a user

```bash
flask change_user_profile <username> -p <profile>
```
This way is the only allowed to promote a user to "Study manager" profile which enable access to some monitoring 
panels in the application.

Profiles that can be set are "Study user" (default for all new user) and "Study manager".

Profile argument is optional, if not set than the user profile will be set to "No profile" which disallow access to all
application features.


## Server configuration
### configuration
SoSTrades application need a configuration file in order to be launch. 
Configuration file is dedicated to a specific environment.
Configuration file is in JSON format. A template of this file is available here:
sostrades_webapi\configuration_template\development_configuration_template.json.
The path to the configuration json file must be set in the SOS_TRADES_SERVER_CONFIGURATION environment variable.

### environment configuration
In addition to the configuration file, some other entry are setup using environment variables:
- FLASK_APP: name of the server into the API (path to the base_server.py)
- FLASK_ENV: name of the environment
- SOS_TRADES_SERVER_CONFIGURATION=Contains the path to the API server json configuration file (the one you want to use)
- SOS_TRADES_DATA=NFS directory where the business data are stored
- SOS_TRADES_REFERENCES=NFS directory where the reference data are stored (predefined business data that are not associated to a user
- SOS_TRADES_EXECUTION_STRATEGY=Execution strategy can be one of those values ‘thread’, ‘subprocess’ and ‘kubernetes’
- EEB_PATH=Execution Engine Block (kubernetes pods yaml configuration file) used to submit container on kubernetes
- SOS_TRADES_RSA=Location of RSA folder with public and private key to encrypt business data on file system
- SQL_ACCOUNT=Depending on the value set in the configuration file, store sql user account
- SQL_PASSWORD=Depending on the value set in the configuration file, store sql user password
- LOG_USER=Depending on the value set in the configuration file, store sql user account
- LOG_PASSWORD=Depending on the value set in the configuration file, store sql user password
- SECRET_KEY=Depending on the value set in the configuration file, store server secret key
- SAML_V2_METADATA_FOLDER=the folder path where the settings.json file is

### SSO configuration
- set the SAML v2 'settings.json' file for the SSO authentication (the file must have this name 'settings.json')
into the folder 'sostrades_webapi\configuration\saml'.
A template of this file is located in the 'sostrades_webapi\configuration_template\saml' folder.
All explanations on how to fill it are accessible here: https://github.com/onelogin/python3-saml.
- in the '.flaskenv' file, set the variable SAML_V2_METADATA_FOLDER with the folder path where the settings.json is.
The path can be relative like: 'sostrades_webapi\configuration_template\saml'.

## Server test configuration
### configuration
As the server configuration, tests need also a configuration file to initialize their environment.
Configuration file is in JSON format. A template of this file is available here:
sostrades_webapi\configuration_template\development_configuration_template.json.

The key regarding LDAP, JWT Token and SMTP server are not needed to be filled.

### environment configuration
As the server configuration some environment variable are needed
In addition to the configuration file, some other entry are setup using environment variables:
- SOS_TRADES_SERVER_CONFIGURATION=Contains the path to the API server json configuration file (the one you want to use)
- SQL_ACCOUNT=Depending on the value set in the configuration file, store sql user account
- SQL_PASSWORD=Depending on the value set in the configuration file, store sql user password
- LOG_USER=Depending on the value set in the configuration file, store sql user account
- LOG_PASSWORD=Depending on the value set in the configuration file, store sql user password
- SECRET_KEY=Depending on the value set in the configuration file, store server secret key

For local development, .flaskenv_unit_test can be filled to make test works.

## Server execution

### APIs

API is split in 4 part
- main_server: for all process related to manipulate study with SoSTrades execution engine
- data_server: for all data management (database CRUD operation)
- post_processing_server: for all process related to manipulate study post-processing
- message_server: websockets implemented for cooperative edition purpose

#Licence
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


