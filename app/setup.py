"""
connections setup functions

MongoDB replicaset notes:
https://pymongo.readthedocs.io/en/stable/examples/high_availability.html#id1

##### If on a linux server, use the hostname provided by the docker compose file #####
e.g. HOSTNAME = mongod1, mongod2, mongod3
URI = 'mongodb://<HOSTNAME>:27017,<HOSTNAME>:27018,<HOSTNAME>:27019/?replicaSet=DBNAME'
URI = 'mongodb://mongod1:27017/?replicaSet=rs0'

##### If on MacOS add the following to the /etc/hosts file #####
127.0.0.1  mongod1
And use localhost as the HOSTNAME
URI = 'mongodb://localhost:27017/?replicaSet=rs0  # 127.0.0.1 can also be used

Add proper authentication details if uname and passwd are used.
"""
import logging
from functools import partial

import pymongo
from pymilvus import connections
from config import (
    MONGO_HOST, MONGO_PORT, MONGO_REPLICASET_NAME,
    MONGO_INITDB_ROOT_USERNAME, MONGO_INITDB_ROOT_PASSWORD,
    MILVUS_HOST, MILVUS_PORT,
    MILVUS_EMB_VECTOR_DIM, MILVUS_EMB_METRIC_TYPE,
    MILVUS_EMB_INDEX_TYPE, MILVUS_EMB_COLLECTION_NAME_FMT,
    MILVUS_EMB_INDEX_PARAM_M, MILVUS_EMB_INDEX_PARAM_EF_CONS)
from config import HF_API_TOKEN, HF_API_URL
from api.milvus import get_milvus_collec_conn
from api.hf_embedding import query_api_online, query_api_docker
from api.html_extraction import SeleniumScraper, RequestsScraper

# logging
logger = logging.getLogger("setup")

# ############## load relevant connections ##############

# connect to milvus
connections.connect(
    alias="default",
    host=MILVUS_HOST,
    port=MILVUS_PORT)

# connect to milvus standalone collection connection standalone
milvus_client = get_milvus_collec_conn(
    collection_name=MILVUS_EMB_COLLECTION_NAME_FMT % 1,
    vector_dim=MILVUS_EMB_VECTOR_DIM,
    metric_type=MILVUS_EMB_METRIC_TYPE,
    index_type=MILVUS_EMB_INDEX_TYPE,
    index_metric_params={
        "M": MILVUS_EMB_INDEX_PARAM_M,
        "efConstruction": MILVUS_EMB_INDEX_PARAM_EF_CONS})

# connect to mongodb replicaset
MONGO_URI = f'mongodb://{MONGO_HOST}:{MONGO_PORT}/?replicaSet={MONGO_REPLICASET_NAME}'
# connect to mongodb standalone
# MONGO_URI = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
mongodb_client = pymongo.MongoClient(
    MONGO_URI,
    username=MONGO_INITDB_ROOT_USERNAME,
    password=MONGO_INITDB_ROOT_PASSWORD)

# ############## load relevant functions ##############

# choose html text extraction function
# prefer selenium but fallback o requests if chromedriver not available
try:
    selenium_scraper = SeleniumScraper()
    get_html_from_url = selenium_scraper.get_html_from_url
except Exception as excep:
    logger.warning(
        "%s: Could not load chromedriver-based selenium html extraction. Reverting to requests extraction", excep)
    requests_scraper = RequestsScraper()
    get_html_from_url = requests_scraper.get_html_from_url

# choose one hf embedding api endpoint
query_hf_emb = partial(query_api_online, hf_api_tkn=HF_API_TOKEN, hf_api_url=HF_API_URL)
query_hf_emb = query_api_docker
