"""
pymilvus api function wrappers
"""
import os
import logging
from typing import List, Dict

import numpy as np
from pymilvus import Collection
from pymilvus import CollectionSchema, FieldSchema, DataType, utility, MilvusException
from utils.common import timeit_decorator


DEBUG: bool = os.environ.get("DEBUG", "") != "False"
logger = logging.getLogger('milvus_api')


def get_milvus_collec_conn(
        collection_name: str,
        vector_dim: int = 128,
        metric_type: str = "IP",
        index_type: str = "HNSW",
        index_metric_params: dict = None) -> Collection:
    """
    Gets the milvus connection with the given collection name otherwise creates a new one
    For using cosine similarity later when metric_type is IP, the embeddings must be normalized as emb / np.linalg.norm(emb)
    """
    if not utility.has_collection(collection_name):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64,
                        description="ids", is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR,
                        description="embedding vectors", dim=vector_dim),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR,
                        description="unique parent doc id", max_length=256),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR,
                        description="unique user id", max_length=128),
            FieldSchema(name="content", dtype=DataType.VARCHAR,
                        description="plaintext data content", max_length=4096),
        ]
        schema = CollectionSchema(
            fields=fields, description='text embedding system')
        milvus_client = Collection(name=collection_name,
                                   consistency_level="Strong",
                                   schema=schema, using='default')
        logger.info("Collection %s created.✅️", collection_name)

        # Index the milvus_client
        index_params = {
            'metric_type': metric_type,
            'index_type': index_type,
            'params': index_metric_params
        }
        milvus_client.create_index(
            field_name="embedding", index_params=index_params)
        logger.info("Collection %s indexed.✅️", collection_name)
    else:
        logger.info("Collection %s present already.✅️", collection_name)
        milvus_client = Collection(collection_name)
    return milvus_client


def create_partition_if_not_exist_milvus(
        milvus_client: Collection,
        partition_name: str,) -> None:
    """
    Creates a partition in the collection milvus_client if it doesn't exist
    Note: if max num of partitions reached in collection (4096), an error will be thrown TODO handle this 
    in the future
    """
    if not milvus_client.has_partition(partition_name):
        milvus_client.create_partition(partition_name)
        logger.info("Partition %s created in collection", partition_name)
    else:
        logger.info("Partition % already exists in collection", partition_name)


def load_partition_milvus(
        milvus_client: Collection,
        partition_name: str,
        partition_replica_number: int = 1):
    """
    load partition into memory
    """
    # TODO fix this, manage partition loading with user sessions instead
    try:
        milvus_client.load([partition_name], replica_number=partition_replica_number)
    except MilvusException as excep:
        # WARNING can be very inefficient
        milvus_client.release()
        logger.warning("%s: Current collection released from memory", excep)
        milvus_client.load([partition_name], replica_number=partition_replica_number)
    logger.info("Partition %s loaded into memory", partition_name)


def insert_into_milvus(
        milvus_client: Collection,
        partition_name: str,
        data: list) -> Dict:
    """
    Insert data with user_id into milvus collection 
    """
    milvus_client.insert(data, partition_name=partition_name)
    logger.info("data inserted into milvus ✅️")
    return {"status": "success",
            "detail": "data inserted in vector db"}


def search_milvus(
        milvus_client: Collection,
        partition_name: str,
        vector_list: List[np.ndarray],
        limit: int = 10,
        dist_thres: float = 0.3,
        search_params: dict = None,
        expr: str = None) -> Dict:
    """
    Searches vector in milvus collection
    """
    results = milvus_client.search(
        data=vector_list,
        anns_field="embedding",
        param=search_params,
        limit=limit,
        expr=expr,
        partition_names=[partition_name] if partition_name else None,
        output_fields=["content", "doc_id"])
    if not results:
        return {"status": "success",
                "detail": "no vector entries found in vector db"}
    results = sorted(results, key=lambda k: k.distances)
    results = [{"distance": res.distance,
                "doc_id": res.entity.get("doc_id"),
                "content": res.entity.get("content")}
               for res in results[0] if res.distance < dist_thres]
    if not results:
        return {"status": "success",
                "detail": "no similar entities found in vector db"}
    return {"status": "success",
            "detail": f"{len(results)} similar entitie(s) found in vector db",
            "content": results}


# if DEBUG is true, function runs are time
if DEBUG:
    get_milvus_collec_conn = timeit_decorator(get_milvus_collec_conn)
    create_partition_if_not_exist_milvus = timeit_decorator(create_partition_if_not_exist_milvus)
    load_partition_milvus = timeit_decorator(load_partition_milvus)
    insert_into_milvus = timeit_decorator(insert_into_milvus)
    search_milvus = timeit_decorator(search_milvus)
