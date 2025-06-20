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
