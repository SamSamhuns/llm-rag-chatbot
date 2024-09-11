"""
Upsert file api
"""
import os
import os.path as osp
import io
import json
import uuid
import logging
import traceback
from typing import List, Dict

from fastapi import APIRouter, Query, File, UploadFile, status, HTTPException
from pypdf import PdfReader

from config import FILE_STORAGE_DIR, MONGO_USER_DB, MONGO_USER_COLLECTION, MONGO_DOC_COLLECTION
from setup import milvus_client, mongodb_client, query_hf_emb, get_html_from_url
from api.milvus import insert_into_milvus
from api.mongo import user_exists_in_mongo
from api.html_extraction import get_text_from_html
from api.yt_transcript import get_text_transcript_from_yt_video
from utils.common import get_file_md5


SUPPORTED_EXT = {".txt", ".pdf"}
router = APIRouter()
logger = logging.getLogger('upsert_route')


# TODO extrac the body function calls in file and url to another func as they are similar
# TODO change to llama index with langchain


@router.post("/files/{user_id}", response_model=Dict,
             status_code=status.HTTP_200_OK,
             summary="Extract text from ['.txt', '.pdf'] file & save emb in a vector db")
async def file_upsert(user_id: str, files: List[UploadFile] = File(...)):
    """
    Extract text from ['.txt', '.pdf'] file & save emb in a vector db
    TODO: add json, pdf support, should add support for other types of files as well i.e. code files
    """
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        if not user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
            status_code = status.HTTP_404_NOT_FOUND
            response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
            raise HTTPException(status_code=status_code, detail=response_data["detail"])

        for file in files:
            file_ext = os.path.splitext(file.filename)[1]
            if file_ext not in SUPPORTED_EXT:
                response_data["detail"] = f"Only files with extensions {SUPPORTED_EXT} supported. {file.filename} is invalid"
                raise ValueError(response_data["detail"])

        user_docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]
        user_doc_dir = osp.join(FILE_STORAGE_DIR, "user_" + user_id)
        partition_name = f"partition_{user_id}"

        emb_files = []
        for file in files:
            mongo_sess = mongodb_client.start_session()
            with mongo_sess.start_transaction():  # atomic mongo transaction
                f_content = file.file.read()
                f_name = file.filename
                # check if file alr exists in the db using md5sum
                fmd5 = get_file_md5(f_content)
                if user_docs.find_one({"doc_md5": fmd5, "user_id": user_id}):
                    logger.info("%s already stored and indexed in db. Skipping", f_name)
                    continue
                doc_id = str(uuid.uuid4())
                fsave_path = osp.join(user_doc_dir, doc_id + osp.splitext(f_name)[-1])

                # insert doc info info into mongodb
                doc_obj = {"_id": doc_id, "user_id": user_id,
                           "doc_name": f_name, "doc_md5": fmd5, "doc_path": fsave_path}
                user_docs.insert_one(doc_obj, session=mongo_sess)

                # TODO improve this, right now they are just saved to the disk with a dir with the user_id as name
                with open(fsave_path, 'wb') as f_write:
                    f_write.write(f_content)

                if osp.splitext(f_name)[-1] == ".pdf":
                    reader = PdfReader(io.BytesIO(f_content))
                    pages_content_str = [page.extract_text() for page in reader.pages]
                    file_content_str = ''.join(pages_content_str)
                else:
                    # decode txt file contents
                    enc = json.detect_encoding(f_content)
                    file_content_str = f_content.decode(enc)
                # TODO improve chunking, check llama index chaining
                # chunking here in sizes of 1024
                chunk_sz = 1024
                content_chunks = [file_content_str[i: i + chunk_sz]
                                  for i in range(0, len(file_content_str), chunk_sz)]
                emb_vecs = [query_hf_emb(chunk) for chunk in content_chunks]
                # save emb in vector database with doc_id & user_id as metadata
                data = [emb_vecs, [doc_id] * len(emb_vecs), [user_id] * len(emb_vecs), content_chunks]
                insert_into_milvus(milvus_client, partition_name, data)
                emb_files.append(f_name)
            mongo_sess.end_session()
        if len(emb_files) > 0:
            response_data["detail"] = f"uploaded and embedded {len(emb_files)} file(s). "
            if len(emb_files) != len(files):
                response_data["detail"] += f"files { {f.filename for f in files} - set(emb_files) } were not uploaded"
            response_data["content"] = emb_files
        else:
            response_data["detail"] = "uploaded files could not be uploaded or already exist in system"
            raise ValueError(response_data["detail"])
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", "failed to upload files to server")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.post("/urls/html/{user_id}", response_model=Dict,
             status_code=status.HTTP_200_OK,
             summary="Extract text from an html page from url & save emb in a vector db")
async def url_html_upsert(user_id: str, urls: List[str] = Query(None)):
    """
    Extract text from an html page from url & save emb in a vector db
    """
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        if not user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
            status_code = status.HTTP_404_NOT_FOUND
            response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
            raise HTTPException(status_code=status_code, detail=response_data["detail"])

        user_docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]
        user_doc_dir = osp.join(FILE_STORAGE_DIR, "user_" + user_id)
        partition_name = f"partition_{user_id}"

        emb_files = []
        for url in urls:
            mongo_sess = mongodb_client.start_session()
            with mongo_sess.start_transaction():  # atomic mongo transaction
                html = get_html_from_url(url)
                f_content = bytes(get_text_from_html(html), "utf-8")
                f_name = str(uuid.uuid4())  # use a unique as the same
                # check if file alr exists in the db using md5sum
                fmd5 = get_file_md5(f_content)
                if user_docs.find_one({"doc_md5": fmd5, "user_id": user_id}):
                    logger.info("%s already stored and indexed in db. Skipping", f_name)
                    continue
                doc_id = str(uuid.uuid4())
                fsave_path = osp.join(user_doc_dir, doc_id + osp.splitext(f_name)[-1])

                # insert doc info info into mongodb
                doc_obj = {"_id": doc_id, "user_id": user_id,
                           "doc_name": f_name, "doc_md5": fmd5, "doc_path": fsave_path}
                user_docs.insert_one(doc_obj, session=mongo_sess)

                # TODO improve this, right now they are just saved to the disk with a dir with the user_id as name
                with open(fsave_path, 'wb') as f_write:
                    f_write.write(f_content)
                enc = json.detect_encoding(f_content)
                file_content_str = f_content.decode(enc)
                # TODO improve chunking, check llama index chaining
                # chunking here in sizes of 1024
                chunk_sz = 1024
                content_chunks = [file_content_str[i: i + chunk_sz]
                                  for i in range(0, len(file_content_str), chunk_sz)]
                emb_vecs = [query_hf_emb(chunk) for chunk in content_chunks]
                # save emb in vector database with doc_id & user_id as metadata
                data = [emb_vecs, [doc_id] * len(emb_vecs), [user_id] * len(emb_vecs), content_chunks]
                insert_into_milvus(milvus_client, partition_name, data)
                emb_files.append(f_name)
            mongo_sess.end_session()
        if len(emb_files) > 0:
            response_data["detail"] = f"uploaded and embedded {len(emb_files)} urls. "
            if len(emb_files) != len(urls):
                response_data["detail"] += f"urls { set(urls) - set(emb_files) } were not uploaded"
            response_data["content"] = emb_files
        else:
            response_data["detail"] = "uploaded urls could not be uploaded or already exist in system"
            raise ValueError(response_data["detail"])
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", "failed to upload urls to server")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data



@router.post("/urls/youtube/{user_id}", response_model=Dict,
             status_code=status.HTTP_200_OK,
             summary="Extract transcript text from a youtube url if available & save emb in a vector db")
async def url_yt_upsert(user_id: str, urls: List[str] = Query(None)):
    """
    Extract text from an html page from url & save emb in a vector db
    """
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        if not user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
            status_code = status.HTTP_404_NOT_FOUND
            response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
            raise HTTPException(status_code=status_code, detail=response_data["detail"])

        user_docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]
        user_doc_dir = osp.join(FILE_STORAGE_DIR, "user_" + user_id)
        partition_name = f"partition_{user_id}"

        emb_files = []
        for url in urls:
            mongo_sess = mongodb_client.start_session()
            with mongo_sess.start_transaction():  # atomic mongo transaction
                f_content = bytes(get_text_transcript_from_yt_video(url), "utf-8")
                f_name = str(uuid.uuid4())  # use a unique as the same
                # check if file alr exists in the db using md5sum
                fmd5 = get_file_md5(f_content)
                if user_docs.find_one({"doc_md5": fmd5, "user_id": user_id}):
                    logger.info("%s already stored and indexed in db. Skipping", f_name)
                    continue
                doc_id = str(uuid.uuid4())
                fsave_path = osp.join(user_doc_dir, doc_id + osp.splitext(f_name)[-1])

                # insert doc info info into mongodb
                doc_obj = {"_id": doc_id, "user_id": user_id,
                           "doc_name": f_name, "doc_md5": fmd5, "doc_path": fsave_path}
                user_docs.insert_one(doc_obj, session=mongo_sess)

                # TODO improve this, right now they are just saved to the disk with a dir with the user_id as name
                with open(fsave_path, 'wb') as f_write:
                    f_write.write(f_content)
                enc = json.detect_encoding(f_content)
                file_content_str = f_content.decode(enc)
                # TODO improve chunking, check llama index chaining
                # chunking here in sizes of 1024
                chunk_sz = 1024
                content_chunks = [file_content_str[i: i + chunk_sz]
                                  for i in range(0, len(file_content_str), chunk_sz)]
                emb_vecs = [query_hf_emb(chunk) for chunk in content_chunks]
                # save emb in vector database with doc_id & user_id as metadata
                data = [emb_vecs, [doc_id] * len(emb_vecs), [user_id] * len(emb_vecs), content_chunks]
                insert_into_milvus(milvus_client, partition_name, data)
                emb_files.append(f_name)
            mongo_sess.end_session()
        if len(emb_files) > 0:
            response_data["detail"] = f"uploaded and embedded {len(emb_files)} youtube transcripts from urls. "
            if len(emb_files) != len(urls):
                response_data["detail"] += f"urls { set(urls) - set(emb_files) } were not uploaded"
            response_data["content"] = emb_files
        else:
            response_data["detail"] = "uploaded youtube transcripts from urls could not be uploaded or already exist in system"
            raise ValueError(response_data["detail"])
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", "failed to upload youtube transcripts from urls to server")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data
