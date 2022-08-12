"""
RESTful API views
"""


import os.path
from sos_trades_api.server.base_server import app




# load all views in this directory
__all__ = [os.path.basename(p)[:-3]
           for p in os.listdir(os.path.dirname(__file__))
           if p.endswith('.py') and not p.startswith('_')]