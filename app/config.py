"""
Load configurations and constants 
"""
import os
from logging.config import dictConfig
from models.logging import LogConfig


# project information
PROJECT_NAME: str = "ChatBot Backend API template"
PROJECT_DESCRIPTION: str = "Template API for ChatBot Backend"
DEBUG: bool = os.environ.get("DEBUG", "") != "False"
VERSION: str = "0.0.1"

# save directories
ROOT_STORAGE_DIR = os.getenv("ROOT_STORAGE_DIR", default="volumes/chatbot_backend")
FILE_STORAGE_DIR = os.getenv("FILE_STORAGE_DIR", default=os.path.join(ROOT_STORAGE_DIR, "user_files"))
LOG_STORAGE_DIR = os.getenv("LOG_STORAGE_DIR", default=os.path.join(ROOT_STORAGE_DIR, "logs"))

os.makedirs(ROOT_STORAGE_DIR, exist_ok=True)
os.makedirs(FILE_STORAGE_DIR, exist_ok=True)
os.makedirs(LOG_STORAGE_DIR, exist_ok=True)

# logging conf
log_cfg = LogConfig()
# override info & error log paths
log_cfg.handlers["info_rotating_file_handler"]["filename"] = os.path.join(LOG_STORAGE_DIR, "info.log")
log_cfg.handlers["warning_file_handler"]["filename"] = os.path.join(LOG_STORAGE_DIR, "error.log")
log_cfg.handlers["error_file_handler"]["filename"] = os.path.join(LOG_STORAGE_DIR, "error.log")
dictConfig(log_cfg.dict())

# redis conf
REDIS_HOST = os.getenv("REDIS_HOST", default="127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", default="6379"))

# milvus conf
MILVUS_HOST = os.getenv("MILVUS_HOST", default="127.0.0.1")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", default="19530"))
ATTU_PORT = int(os.getenv("MILVUS_PORT", default="3000"))

# milvus vector conf
MILVUS_EMB_VECTOR_DIM = 384
MILVUS_EMB_METRIC_TYPE = "IP"
MILVUS_EMB_INDEX_TYPE = "HNSW"
MILVUS_EMB_INDEX_PARAM_M = 8
MILVUS_EMB_INDEX_PARAM_EF_CONS = 64
MILVUS_EMB_SEARCH_PARAM_EF = 32
MILVUS_EMB_COLLECTION_NAME_FMT = "collection_%05d"

# mongodb conf
MONGO_REPLICASET_NAME = "rs0"
MONGO_HOST = os.getenv("MONGO_HOST", default="127.0.0.1")
MONGO_PORT = int(os.getenv("MONGO_PORT", default="27017"))
MONGO_INITDB_ROOT_USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", default="root")
MONGO_INITDB_ROOT_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", default="admin")
MONGO_USER_DB = os.getenv("MONGO_USER_DB", default="user_db")
MONGO_USER_COLLECTION = os.getenv("MONGO_USER_COLLECTION", default="users")
MONGO_DOC_COLLECTION = os.getenv("MONGO_DOC_COLLECTION", default="docs")

# huggingface conf
HF_API_TOKEN = os.getenv("HF_API_TOKEN", default="HUGGINGFACE_API_KEY")
HF_API_URL = os.getenv("HF_API_URL", default="HUGGINGFACE_API_URL_ENDPOINT")
