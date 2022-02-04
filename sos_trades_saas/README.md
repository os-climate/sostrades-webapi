<<<<<<< HEAD
# SoSTrades SAAS
=======
# SoSTrades_SAAS
>>>>>>> cf64e9d (route to study)


## Purpose

<<<<<<< HEAD
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
    - *data*: dictionary of editable input or numerical discipline
    - *children*: list of children data
  - *study_name* : loaded study name


=======
This API is designed to offer some acces point.
TBC...

## Exposed routes

### GUI study link

1/ url 
2/ response content
3/ misc
>>>>>>> cf64e9d (route to study)


