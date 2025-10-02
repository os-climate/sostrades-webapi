# SoSTrades SAAS



## Purpose

This API is designed to offer some access point for command line requests.


## Exposed routes

### Authorization

Each request has to be authorize using an api key provided using Authorization header

- Authorization header : 
  'Authorization': 'Bearer <api_key>'
  
Api key has to be created and provided using flask command:

**For group-based API keys (legacy):**
```bash
flask create_api_key <group_name> <api_key_name>
```

**For user-based API keys (recommended):**
```bash
flask create_user_api_key <username> <api_key_name>
```

**Note:** User-based API keys provide better security isolation and are the recommended approach for new integrations.

### Load a study case

Study case loading route allow requesting disciplines values of a study.

    https://<host>/api/v0/study-case/<int:study_id>
    https://<host>/api/v0/study-case/<int:study_id>/<int:timeout>

- GET parameters : 
  - *study_id* : study identifier (integer) 
  - *timeout* : timeout in seconds, optional, default 30s (integer) 

- response content : json content with disciplines as keys, disciplines data as value or an empty response if study did not load within time.

```python
import requests, json

# Its assumed that a bearer token as been previously requested
response = requests.get(
    "https://<host>/api/v0/study-case/<int:study_id>",
    headers={"Authorization": "Bearer <api_key>"})

print(json.dumps(response.json(), indent=4))
# Printed response should be like
# {
# "my.discipline.1": {
#        "optional": false,
#        "type": "string",
#        "unit": null,
#        "value": "SimpleCache",
#        "var_name": "cache_type",
#        "visibility": "Local"
#    },
# "my.discipline.2": {
#        "optional": false, ... 
```

### Download a study case file parameter

Study case downloading route allow requesting disciplines files content.

    https://<host>/api/v0/study-case/<int:study_id>/parameter/download

- POST parameters : 
  - *parameter_key* : parameter identifier

- response content : file content for parameter

```python
import requests, json

# Its assumed that a bearer token as been previously requested
response = requests.post(
    "https://<host>/api/v0/study-case/<int:study_id>/parameter/download",
    json={"parameter_key": "my.study.discipline"},
    headers={"Authorization": "Bearer <api_key>"})

print(response.content.decode("utf-8"))
# Printed content should be like

# years,quantity
# 1982,10.0
# 1983,10.0
# 1984,5.0
# 1985,5.0
```

### Update study case parameters

Study case update parameters route allow modifying either scalar or csv parameter.

    https://<host>/api/v0/study-case/<int:study_id>/parameters

- POST parameters (scalar case): list of
  - *variableId* : parameter identifier (can be retrieved by loading study case)
  - *unit* : parameter unit
  - *newValue* : parameter new value
- POST parameters (csv file case): dictionary of
  - *parameter* : *file-like*

```python
import requests

# Its assumed that a bearer token as been previously requested
# Scalar parameter
response = requests.post(
    "https://<host>/api/v0/study-case/<int:study_id>/parameters",
    json=[{
                "variableId": "my.study.discipline",
                "unit": "the_unit",
                "newValue": "the_new_value"
            }],
    headers={"Authorization": "Bearer <api_key>"})

# File parameter
response = requests.post(
    "https://<host>/api/v0/study-case/<int:study_id>/parameters",
    files={
            "my.study.discipline": open("/path/to/my/file.csv", "rb"),
        },
    headers={"Authorization": "Bearer <api_key>"})

```

### Get study case (GUI) url

Provide a html link to SoSTradesGui for a study case.

    https://<host>/api/v0/study-case/<int:study_id>/url

- GET parameters : 
  - *study_id* : study identifier (integer) 

- response content :
  - *study_url* : url for study case
  
### Execute study case calculation

Trigger the calculation execution for a study case.

    https://<host>/api/v0/calculation/execute/<int:study_id>

- POST parameters : 
  - None

- response content : same as monitoring

```python
import requests

# Its assumed that a bearer token as been previously requested
response = requests.post(
    "https://<host>/api/v0/calculation/execute/<int:study_id>",
    headers={"Authorization": "Bearer <api_key>"})
```

### Monitor study case calculation status

Report execution status for a study case.

    https://<host>/api/v0/calculation/status/<int:study_id>

- GET parameters : 
  - *study_id* : study identifier (integer) 

- response content :
  - *disciplines_status* : status by discipline
  - *study_case_execution_status* : study status
  - *study_case_id* : study identifier

```python
import requests

# Its assumed that a bearer token as been previously requested
response = requests.get(
    "https://<host>/api/v0/calculation/status/<int:study_id>",
    headers={"Authorization": "Bearer <api_key>"})

print(response.json())
# Printed response should be like
# {
#     "disciplines_status": {
#         "disc1": "DONE",
#         "disc2": "PENDING",
#         ....
#     },
#     "study_case_execution_cpu": "1.1/8",
#     "study_case_execution_memory": "6.94/7.81 [GB]",
#     "study_case_execution_status": "FINISHED",
#     "study_case_id": 21
# }
```

### Load study case post-processing

Study case post-processing loading route allow requesting post-processing data by disciplines.

    https://<host>/api/v0/post-processing/<int:study_id>

- GET parameters : 
  - *study_id* : study identifier (integer)

- response content : complex json content with disciplines as keys, disciplines post-processing data as value.

```python
import requests

# Its assumed that a bearer token as been previously requested
response = requests.get(
    "https://<host>/api/v0/post-processing/<int:study_id>",
    headers={"Authorization": "Bearer <api_key>"})

print(response.json())
# Printed response should be like
# {
# "my.discipline.1": { post_processing_data },
# "my.discipline.2": { post_processing_data },
# ... 
```

### Load study case post-processing in html 

Provide post-processing graphs in a templated html. 

    https://<host>/api/v0/post-processing/<int:study_id>/html

- GET parameters : 
  - *study_id* : study identifier (integer)

- response content : html templated graphs

```python
import requests

# Its assumed that a bearer token as been previously requested
response = requests.get(
    "https://<host>/api/v0/post-processing/<int:study_id>/html",
    headers={"Authorization": "Bearer <api_key>"})

# Create an html file
with open("/path/to/my/file", "w") as fs:
    fs.write(response.text)
```

