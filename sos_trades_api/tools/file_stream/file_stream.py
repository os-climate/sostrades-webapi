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
import hashlib
import os
import zipfile
from os.path import isdir, relpath


def zip_files_and_folders(zip_file_path, files_or_folders_path_to_zip):
    """
        function that zip all files and folders in the list into one archive
        
        Args:
            zip_file_path (str): path to the zip file to be written
            files_or_folders_path_to_zip (list[str]): list of files or folders path to write in the archive
    """
    # # Create a temporary directory to organize files: too slow
    # with tempfile.TemporaryDirectory() as temp_dir:
    #     # Copy all files and folders to the temp directory
    #     for path in files_or_folders_path_to_zip:
    #         dest = os.path.join(temp_dir, os.path.basename(path))
    #         if os.path.isdir(path):
    #             shutil.copytree(path, dest)
    #         else:
    #             shutil.copy2(path, dest)
    #     # Remove .zip extension if present for make_archive
    #     base_name = os.path.join(zip_file_path, f'study_export_{os.path.basename(temp_dir)}')      
        
    #     # Create the zip archive
    #     return shutil.make_archive(base_name, 'zip', temp_dir)
    
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
            zip_folder(zip_file, file_or_folder_path, file_or_folder_path)
        else:
            zip_file.write(file_or_folder_path, os.path.basename(file_or_folder_path))
    # close the zip file
    zip_file.close()



def generate_large_file(file_path):
    with open(file_path, "rb") as f:
        while chunk := f.read(50 * 1024 * 1024):  # read by blocs of 50 Mo
            yield chunk


def get_file_hash(filename, algorithm='sha256', block_size=65536):
    """
    Calculate the hash of a file using the specified algorithm.
    
    Args:
        filename (str): Path to the file
        algorithm (str): Hash algorithm to use (default: sha256)
        block_size (int): Size of blocks to read (default: 64KB)
        
    Returns:
        str: Hexadecimal digest of the file hash
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(filename, 'rb') as file:
        for block in iter(lambda: file.read(block_size), b''):
            hash_obj.update(block)
            
    return hash_obj.hexdigest()

def verify_files_after_copy(original_path, copy_path, algorithm='sha256'):
    """
    Verify that a copied file is identical to the original by comparing hashes.
    
    Args:
        original_path (str): Path to the original file
        copy_path (str): Path to the copied file
        algorithm (str): Hash algorithm to use (default: sha256)
        
    Returns:
        bool: True if files are identical, False otherwise
    """
    # Check if both files exist
    if not os.path.exists(original_path):
        raise FileNotFoundError(f"Original file not found: {original_path}")
    if not os.path.exists(copy_path):
        raise FileNotFoundError(f"Copied file not found: {copy_path}")
    
    # Calculate hashes
    original_hash = get_file_hash(original_path, algorithm)
    copy_hash = get_file_hash(copy_path, algorithm)
    
    # Compare hashes
    return original_hash == copy_hash
