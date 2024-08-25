from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DETAILS = "mongodb+srv://gangeshk:iUK8GV65TygL3BHC@cluster0.ohd32.mongodb.net/"
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.my_database_name  # Replace with your database name

def get_collection(name: str):
    return database[name]
