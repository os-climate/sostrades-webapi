'''
Copyright 2023 Capgemini

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

import glob
import os
import re
from datetime import datetime, timedelta

from sos_trades_api.config import Config

ACTIVE_STUDY_FILE_NAME = "active_study_"
LOG_FILE_NAME = "logs_"
DATETIME_STR_FORMAT = "%m/%d/%y %H:%M:%S"


def check_studies_last_active_date( delay_hr, logger):
    """
    Read the active_study_date if it exists into the local folder file name active_study_{study_id}
    Check if the date is past a certain delay in hours from the current date
    :param study_id: id of the study to retreive the file name
    :type: int
    :param delay_hr: delay in hour
    :type: int
    """
    inactive_study_ids = []
    local_path = Config().local_folder_path

    if local_path != "" and os.path.exists(local_path):
        # iterate on all files of active study (should be only one existing)
        for file in glob.glob(os.path.join(local_path, f"{ACTIVE_STUDY_FILE_NAME}*.txt"),recursive=False):
            last_active_date = None
            is_inactive = False

            try:
                # read the file and get the last_active date
                with open(file) as f:
                    last_active_date_str = f.readline().strip()
                    logger.debug(f"written date:{last_active_date_str}")
                    last_active_date = datetime.strptime(last_active_date_str, DATETIME_STR_FORMAT)

            except Exception as exception:
                logger.info(f"An error append while checking active date:{exception!s}")
                log_file = os.path.join(local_path, f"{LOG_FILE_NAME}{os.path.basename(file)}")
                with open(log_file, "a") as f:
                    f.write(f"{datetime.now()}-check last active date error: {exception!s}\n")
                raise Exception(f"Log error is written in {log_file} file")


            # check if the date is past the delay of inactivity
            if last_active_date is not None:
                delta_time = datetime.now() - timedelta(hours=delay_hr)
                is_inactive = last_active_date < delta_time

            #if the study is inactive for too long, get the associated study_id
            if is_inactive:
                # search for number in the file name
                match = re.search(r"\d+", os.path.basename(file))
                if match:
                    #the number represents the study id
                    study_id = int(match.group())
                    inactive_study_ids.append(study_id)

    return inactive_study_ids

def delete_study_last_active_file(study_id):
    """
    delete the file named active_study_{study_id}
    """
    local_path = Config().local_folder_path
    file_path = os.path.join(local_path, f"{ACTIVE_STUDY_FILE_NAME}{study_id}.txt")
    if os.path.exists(file_path):
        os.remove(file_path)
    log_file_path = os.path.join(local_path, f"{LOG_FILE_NAME}{ACTIVE_STUDY_FILE_NAME}{study_id}.txt")
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

def save_study_last_active_date(study_id, last_active_date):
    """
    write active date in the file
    :param study_id: id of the study to retreive the file name
    :type: int
    :param last_active_date: last_active_date to save in the file
    :type: datetime
    """
    local_path = Config().local_folder_path
    if local_path != "" and os.path.exists(local_path):
        file_path = os.path.join(local_path, f"{ACTIVE_STUDY_FILE_NAME}{study_id}.txt")
        active_date_str = datetime.strftime(last_active_date, DATETIME_STR_FORMAT)
        with open(file_path, "w") as f:
            f.write(f"{active_date_str}")




    """
    Read the active_study_date if it exists into the local folder file name active_study_{study_id}
    """
    active_date = None

    return active_date



