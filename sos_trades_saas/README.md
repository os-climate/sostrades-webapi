# SoSTrades SAAS


## Purpose

This API is designed to offer some access point for command line requests.


## Exposed routes

### Authentication


    https://<host>/saas/login


- POST parameters : 
  - *username* : user name 
  - *password* : user password 

- response content :
  - *access_token* : bearer access token


### GUI study link


    https://<host>/saas/study-case-link/<study_id>


- GET parameters : 
  - *study_id* : study identifier (integer) 

- response content :
  - *study_url* : study gui link

### Load a study


    https://<host>/saas/load-study-case/<study_id>


- GET parameters : 
  - *study_id* : study identifier (integer) 

- response content :
  - *missing_key_here* : loaded study content 

- loaded study content description :
  - *treenode* : 
  - *etc...* :




