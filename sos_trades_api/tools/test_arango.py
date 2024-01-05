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
from arango import ArangoClient

# Install package pip install python-arango

pwd="ArangoDB_BfPM"

# Initialize the ArangoDB client.
#client = ArangoClient(hosts='http://arangodb-instance:8529')
client = ArangoClient(hosts='http://127.0.0.1:8529')

# Connect to "_system" database as root user.
# This returns an API wrapper for "_system" database.
sys_db = client.db('_system', username='root', password=pwd)

# Create a new database named "test" if it does not exist.
if not sys_db.has_database('os-climate'):
    sys_db.create_database('os-climate')

# Connect to "test" database as root user.
# This returns an API wrapper for "test" database.
db = client.db('os-climate', username='root', password=pwd)

# Create a new collection named "datasets" if it does not exist.
# This returns an API wrapper for "datasets" collection.
if db.has_collection('datasets'):
    datasets = db.collection('datasets')
else:
    datasets = db.create_collection('datasets')

datasets.insert({'name': 'jan', 'age': 19})
datasets.insert({'name': 'josh', 'age': 18})
datasets.insert({'name': 'jake', 'age': 21})

# Execute an AQL query. This returns a result cursor.
cursor = db.aql.execute('FOR doc IN datasets RETURN doc')

# Iterate through the cursor to retrieve the documents.
datasets_names = [document['name'] for document in cursor]
print("Datasets names", datasets_names)

sys_db.delete_database('os-climate')

print("has_database after delete :", sys_db.has_database('os-climate'))
