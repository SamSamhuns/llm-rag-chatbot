"""
Vector and doc DB search api endpoints
"""
import logging
import traceback
from typing import Dict, List, Optional

from fastapi import APIRouter, Query, status, HTTPException

from config import MILVUS_EMB_METRIC_TYPE, MILVUS_EMB_SEARCH_PARAM_EF, MONGO_USER_DB, MONGO_USER_COLLECTION
from setup import milvus_client, mongodb_client, query_hf_emb
from api.milvus import search_milvus, load_partition_milvus
from api.mongo import user_exists_in_mongo


router = APIRouter()
logger = logging.getLogger('search_route')


@router.post("/{user_id}", response_model=Dict,
             status_code=status.HTTP_200_OK,
             summary="Extract query emb & find most similar embs from vector db")
async def search(
    user_id: str,
    query: str,
    top_k: int = 5,
    doc_id_list: Optional[List[str]] = Query(None)):
    """Extract query emb & find most similar embs from vector db"""
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        if not user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
            status_code = status.HTTP_404_NOT_FOUND
            response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
            raise HTTPException(status_code=status_code, detail=response_data["detail"])

        partition_name = f"partition_{user_id}"
        if not milvus_client.has_partition(partition_name):
            logger.error("%s: User partition missing in milvus db. Control should not reach here.", traceback.print_exc())
            response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
            raise ValueError(response_data["detail"])
        # TODO very inefficient to load partition like this, consider using user sessions
        load_partition_milvus(milvus_client, partition_name)

        # TODO current if query is longer than emb model input size, it is auto-truncated
        query_vec = query_hf_emb(query)
        # optionally filter searches/hybrid search with conditions i.e. specific docs only
        expr = None if doc_id_list is None else f"doc_id in {doc_id_list}".replace("'", '"')

        search_results = search_milvus(
            milvus_client, partition_name, [query_vec], limit=top_k, dist_thres=3,
            search_params={"metric_type": MILVUS_EMB_METRIC_TYPE, "ef": MILVUS_EMB_SEARCH_PARAM_EF}, expr=expr)

        response_data = search_results
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", "failed to conduct query search in server")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data
