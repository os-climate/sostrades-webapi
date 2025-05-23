'''
Copyright 2025 Capgemini
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
import gzip
import io
import json
import os
import zipfile
from os.path import dirname, isdir, relpath
from typing import Any

from flask import Response

from sos_trades_api.models.custom_json_encoder import CustomJsonEncoder
from sos_trades_api.server.base_server import app
from sos_trades_api.tools.code_tools import time_function


@time_function(app.logger)
def make_gzipped_response(obj:Any):
    """
    Generates a gzipped json response from an object
    """
    json_data = json.dumps(obj, cls=CustomJsonEncoder)
    gzip_buffer = io.BytesIO()
    
    with gzip.GzipFile(mode='w', fileobj=gzip_buffer) as gz:
        gz.write(json_data.encode('utf-8'))
    
    response = Response(gzip_buffer.getvalue(), content_type='application/json')
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(gzip_buffer.getvalue())
    return response

def send_zip_file_content(zip_content: bytes, filename: str = None):
    """
    Generates a gzipped response from zip file content bytes
    
    Args:
        zip_content: The raw bytes content of a zip file
        filename: Optional filename to suggest in the Content-Disposition header
        
    Returns:
        Response object with gzipped zip content
    """
    # Create a BytesIO buffer for gzipping
    gzip_buffer = io.BytesIO()
    try:
        # Compress the zip content
        with gzip.GzipFile(mode='w', fileobj=gzip_buffer) as gz:
            gz.write(zip_content)
        
        gzipped_data = gzip_buffer.getvalue()
        
        # Create response with appropriate headers for a zip file
        response = Response(gzipped_data)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(gzipped_data)
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Vary'] = 'Accept-Encoding'
        
        # Add Content-Disposition header if filename is provided
        if filename:
            if not filename.endswith('.zip'):
                filename += '.zip'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        # Handle compression errors
        raise Exception(f"Failed to compress zip content: {str(e)}")
    finally:
        # Ensure buffer is closed
        if 'gzip_buffer' in locals():
            gzip_buffer.close()

def zip_files_and_folders(zip_file_path, files_or_folders_path_to_zip, metadata = None):
    """
        function that zip all files and folders in the list into one archive
        
        Args:
            zip_file_path (str): path to the zip file to be written
            files_or_folders_path_to_zip (list[str]): list of files or folders path to write in the archive
            metadata (str or bytes): metadata content to add in a metadata.json file
    """
    
    def zip_folder(zip_file, folder_path, root_path):
        """
        function that zip all files in a folder and its sub folders
        
        Args:
            zip_file (zipfile.ZipFile): zip file to be written
            folder_path (str): path of the folder to zip
            root_path (str): path of the root folder to zip to reproduce the folder organization into the zip file
        """
        for element in os.scandir(folder_path):
            if isdir(element):
                zip_folder(zip_file, element.path, root_path)
            else:
                zip_file.write(element.path, 
                    relpath(element.path, root_path))

    # create zip file
    zip_file = zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True, compresslevel=1)

    # iterate throught each element of the list
    for file_or_folder_path in files_or_folders_path_to_zip:
        if isdir(file_or_folder_path):
            zip_folder(zip_file, file_or_folder_path, dirname(file_or_folder_path))
        else:
            zip_file.write(file_or_folder_path, os.path.basename(file_or_folder_path))

    # add metadata file
    if metadata is not None:
        zip_file.writestr("metadata.json", metadata)
        
    # close the zip file
    zip_file.close()

