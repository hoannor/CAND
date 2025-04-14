# This file is intentionally empty to make the directory a Python package 

from .mongodb import Database

# Export the Database class and its methods
get_database = Database.get_database
connect_to_mongo = Database.connect_to_mongo
close_mongo_connection = Database.close_mongo_connection
db = Database()

__all__ = ['get_database', 'connect_to_mongo', 'close_mongo_connection', 'db'] 