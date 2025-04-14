from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_to_mongo(cls):
        """Kết nối tới MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            # Kiểm tra kết nối
            await cls.client.admin.command('ping')
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    @classmethod
    async def close_mongo_connection(cls):
        """Đóng kết nối MongoDB"""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("MongoDB connection closed")

    @classmethod
    async def get_database(cls):
        """Lấy instance của database"""
        if cls.db is None:
            await cls.connect_to_mongo()
        return cls.db

    @classmethod
    async def get_collection(cls, collection_name: str):
        """Lấy collection từ database"""
        db = await cls.get_database()
        return db[collection_name]

db = Database()

async def get_database():
    """Hàm helper để lấy instance của database"""
    return await Database.get_database() 