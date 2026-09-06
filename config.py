import os
from dotenv import load_dotenv

load_dotenv()

# App identity — injected by Jenkins/Kubernetes
APP_VERSION   = os.getenv("APP_VERSION", "v1")
BUILD_NUMBER  = os.getenv("BUILD_NUMBER", "0")
ENVIRONMENT   = os.getenv("ENVIRONMENT", "development")
HOSTNAME      = os.getenv("HOSTNAME", "localhost")

# Database
MONGO_URL     = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "eventapp")

# Server
PORT          = int(os.getenv("PORT", "8000"))
WORKERS       = int(os.getenv("WORKERS", "2"))
