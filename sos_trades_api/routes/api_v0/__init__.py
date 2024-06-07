"""
RESTful API views
"""

import os

# load all views in this directory
__all__ = [os.path.basename(p)[:-3]
           for p in os.listdir(os.path.dirname(__file__))
           if p.endswith(".py") and not p.startswith("_")]
