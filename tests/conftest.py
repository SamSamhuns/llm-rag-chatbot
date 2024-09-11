"""
Test configurations
"""
import os
import shutil
import requests
import pytest
import pytest_asyncio
from httpx import AsyncClient

import pymongo
from pymilvus import connections, utility
from bs4 import BeautifulSoup

import sys
sys.path.append("app")

# custom settings
TEST_USER_ID = "0"
TEST_MILVUS_EMB_COLLECTION_NAME_FMT = "test_%05d"
TEST_MILVUS_COLLECTION_NAME = TEST_MILVUS_EMB_COLLECTION_NAME_FMT % 1
TEST_MONGO_USER_DB = "test_user_db"
TEST_MONGO_USER_COLLECTION = "test_users"
TEST_MONGO_DOC_COLLECTION = "test_docs"

# chg milvus and mongodb params for test duration
os.environ["MILVUS_EMB_COLLECTION_NAME_FMT"] = TEST_MILVUS_EMB_COLLECTION_NAME_FMT
os.environ["MONGO_USER_DB"] = TEST_MONGO_USER_DB
os.environ["MONGO_USER_COLLECTION"] = TEST_MONGO_USER_COLLECTION
os.environ["MONGO_DOC_COLLECTION"] = TEST_MONGO_DOC_COLLECTION

# custom imports
import app.config as cfg
from app.server import app
from app.api.milvus import get_milvus_collec_conn


def _load_file_content(fpath: str) -> bytes:
    """
    Load file from fpath and return as bytes
    """
    with open(fpath, 'rb') as fptr:
        file_content = fptr.read()
    return file_content


@pytest_asyncio.fixture(scope="function")
async def test_app_asyncio():
    """Async test client for the FastAPI app.
    for httpx>=20, follow_redirects=True (cf. https://github.com/encode/httpx/releases/tag/0.20.0)

    Returns: 
        ac (AsyncClient): An async test client for the FastAPI app.
    """
    async with AsyncClient(app=app, base_url="http://test", follow_redirects=True) as ac:
        yield ac  # testing happens here


@pytest.fixture(scope="session")
def test_milvus_conn():
    """Yields a milvus collection connection instance"""
    print("Setting milvus connection & creating collection if it already doesn't exist")
    connections.connect(
        alias="default",
        host=cfg.MILVUS_HOST,
        port=cfg.MILVUS_PORT)

    milvus_collec_conn = get_milvus_collec_conn(
        collection_name=TEST_MILVUS_COLLECTION_NAME,
        vector_dim=cfg.MILVUS_EMB_VECTOR_DIM,
        metric_type=cfg.MILVUS_EMB_METRIC_TYPE,
        index_type=cfg.MILVUS_EMB_INDEX_TYPE,
        index_metric_params={
            "M": cfg.MILVUS_EMB_INDEX_PARAM_M,
            "efConstruction": cfg.MILVUS_EMB_INDEX_PARAM_EF_CONS})
    milvus_collec_conn.load()
    yield milvus_collec_conn
    # drop test collections in teardown
    print("Tearing milvus connection")
    utility.drop_collection(TEST_MILVUS_COLLECTION_NAME)
    connections.disconnect("default")


@pytest.fixture(scope="session")
def test_mongodb_conn():
    """Yields a pymongo connection instance"""
    print("Setting mongodb connection & creating dbs+collecs")
    mongodb_client = pymongo.MongoClient(
        f"mongodb://{cfg.MONGO_HOST}:{cfg.MONGO_PORT}/",
        username=cfg.MONGO_INITDB_ROOT_USERNAME,
        password=cfg.MONGO_INITDB_ROOT_PASSWORD)

    # create user and doc collections
    db = mongodb_client[TEST_MONGO_USER_DB]
    _ = db[TEST_MONGO_USER_COLLECTION]
    _ = db[TEST_MONGO_DOC_COLLECTION]
    yield mongodb_client
    # drop test db in teardown
    print("Tearing mongodb connection")
    mongodb_client.drop_database(TEST_MONGO_USER_DB)
    mongodb_client.close()
    # delete persistent data files
    shutil.rmtree(os.path.join(cfg.FILE_STORAGE_DIR, f"user_{TEST_USER_ID}"))


@pytest.fixture(scope="session")
def mock_user_data_dict():
    """
    returns a func to create a user data dict for testing
    """
    def _gen_data(user_id: str = TEST_USER_ID):
        user_data = {"user_id": user_id,
                     "user_name": "test_user",
                     "user_email": "test+email@testdomain.com"}
        return user_data
    return _gen_data


@pytest_asyncio.fixture(scope="session")
def mock_json_file(tmpdir_factory):
    """
    Returns the content of a JSON file from a placeholder URL.
    """
    # TODO replace url
    url = "https://datatracker.ietf.org/doc/html/rfc1034"
    return requests.get(url, timeout=180).content


@pytest_asyncio.fixture(scope="session")
def mock_pdf_file(tmpdir_factory):
    """
    Returns the content of a PDF file from a placeholder URL.
    """
    # TODO replace url
    url = "https://datatracker.ietf.org/doc/html/rfc1034"
    return requests.get(url, timeout=180).content


@pytest_asyncio.fixture(scope="session")
def mock_txt_file(tmpdir_factory):
    """
    Returns the text content from a URL.
    """
    url = "https://raw.githubusercontent.com/pytorch/vision/main/README.md"
    html_content = requests.get(url, timeout=180).content
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = bytes(soup.get_text(), 'utf-8')

    file_name = "readme.txt"
    file_path = tmpdir_factory.mktemp("html_txt").join(file_name)
    with open(file_path, "wb") as fptr:
        fptr.write(text_content)
    return str(file_path), text_content
