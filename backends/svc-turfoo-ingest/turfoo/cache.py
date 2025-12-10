import redis

from turfoo import settings

# Test connection
try:
    print("Testing Redis connection...")
    print(f"Connecting to Redis at {settings.conf.redis_url}")
    r = redis.from_url(settings.conf.redis_url, decode_responses=True)
    r.ping()
    print("✅ Redis connected")

    # Test set/get
    r.set("test_key", "test_value")
    val = r.get("test_key")
    print(f"✅ Set/Get works: {val}")


    r.delete("test_key")
    print("✅ Redis test complete")

except redis.ConnectionError as e:
    print(f"❌ Redis connection failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
