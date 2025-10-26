# src/finhelp/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

# MongoDB client
client = None
db = None


async def connect_to_mongo():
    """Connect to MongoDB Atlas."""
    global client, db
    try:
        mongodb_uri = settings.MONGODB_URI  # Changed from os.getenv
        
        client = AsyncIOMotorClient(mongodb_uri)
        db = client.finhelp
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas")
        
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


def get_database():
    """Get database instance."""
    return db