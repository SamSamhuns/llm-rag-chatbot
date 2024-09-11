"""
Upsert file api
"""
import os
import shutil
import logging
import traceback
from typing import Dict

from fastapi import APIRouter, status, HTTPException
from email_validator import validate_email, EmailNotValidError

from config import FILE_STORAGE_DIR, MONGO_USER_DB, MONGO_USER_COLLECTION, MONGO_DOC_COLLECTION
from setup import milvus_client, mongodb_client
from api.milvus import create_partition_if_not_exist_milvus, load_partition_milvus
from api.mongo import user_exists_in_mongo


router = APIRouter()
logger = logging.getLogger('users_route')


@router.get("/{user_id}", response_model=Dict,
            status_code=status.HTTP_200_OK,
            summary="Gets the registered user with the given user_id")
async def get_registered_user(user_id: str):
    """Gets the registered user with the given user_id"""
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        users = mongodb_client[MONGO_USER_DB][MONGO_USER_COLLECTION]
        user = users.find_one({"_id": user_id})
        if not user:
            status_code = status.HTTP_404_NOT_FOUND
            response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
            raise HTTPException(status_code=status_code, detail=response_data["detail"])
        user['_id'] = str(user['_id'])
        response_data["detail"] = f"user with id {user_id} found in db"
        response_data["content"] = user
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", f"failed to get information for user with id {user_id}")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.get("", response_model=Dict,
            status_code=status.HTTP_200_OK,
            summary="Gets all the registered users with their respective user_ids")
async def get_all_registered_user():
    """Gets all the registered users with their respective user_ids"""
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        users = mongodb_client[MONGO_USER_DB][MONGO_USER_COLLECTION]
        user_list = list(users.find({}, {"_id": 1, "name": 1, "email": 1}))
        response_data["detail"] = "users currently registered in db"
        response_data["content"] = user_list
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", "failed to get information for all users")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.get("/{user_id}/documents/{doc_id}", response_model=Dict,
            status_code=status.HTTP_200_OK,
            summary="Gets all the document with id: doc_id for user with id: user_id")
async def get_user_document(
        user_id: str,
        doc_id: str):
    """Gets all the document with id: doc_id for user with id: user_id"""
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        if not user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
            status_code = status.HTTP_404_NOT_FOUND
            response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
            raise HTTPException(status_code=status_code, detail=response_data["detail"])
        docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]
        doc = docs.find_one({"_id": doc_id})
        if not doc:
            status_code = status.HTTP_404_NOT_FOUND
            response_data["detail"] = f"doc with id: {doc_id} does not exist in db for user {user_id}."
            raise HTTPException(status_code=status_code, detail=response_data["detail"])
        doc['_id'] = str(doc['_id'])
        response_data["detail"] = f"doc with id {doc_id} for user with id {user_id} found in db"
        response_data["content"] = doc
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", f"failed to get information for user with id {user_id}")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.get("/{user_id}/documents", response_model=Dict,
            status_code=status.HTTP_200_OK,
            summary="Gets all the uploaded documents for user with id: user_id")
async def get_all_user_documents(user_id: str):
    """Gets all the uploaded documents for user with id: user_id"""
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        if not user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
            status_code = status.HTTP_404_NOT_FOUND
            response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
            raise HTTPException(status_code=status_code, detail=response_data["detail"])
        docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]
        doc_list = list(docs.find({"user_id": user_id}, {"_id": 1, "user_id": 1,
                        "doc_name": 1, "doc_md5": 1, "doc_path": 1}))
        response_data["detail"] = f"documents for registered user with id: {user_id}"
        response_data["content"] = doc_list
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", f"failed to get document list info for user with id {user_id}")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.post("", response_model=Dict,
             status_code=status.HTTP_200_OK,
             summary="Register user into system with unique user_id")
async def register_user(
        user_id: str,
        user_name: str,
        user_email: str):
    """
    Register user into system with unique user_id.
    Additional profile on user can also be stored.
    """
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        mongo_sess = mongodb_client.start_session()
        with mongo_sess.start_transaction():  # atomic mongo transaction
            if user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
                status_code = status.HTTP_400_BAD_REQUEST
                response_data["detail"] = f"user with id: {user_id} already exists in db"
                raise HTTPException(status_code=status_code, detail=response_data["detail"])
            # register user into mongodb database if they dont alr exist
            users = mongodb_client[MONGO_USER_DB][MONGO_USER_COLLECTION]
            # validate email
            try:
                # Make DNS queries to ensure email is valid for account creation pages (but not login pages).
                # TODO set to True during production
                emailinfo = validate_email(user_email, check_deliverability=False)
                # use normalized form of the email address before db save.
                user_email = emailinfo.normalized
            except EmailNotValidError as excep:
                status_code = status.HTTP_400_BAD_REQUEST
                response_data["detail"] = f"email {user_email} is invalid"
                raise HTTPException(status_code=status_code, detail=response_data["detail"]) from excep
            # user profile info
            user_obj = {"_id": user_id,
                        "name": user_name,
                        "email": user_email}
            users.insert_one(user_obj, session=mongo_sess)
            # create partition for user in milvus if it doesn't alr exist
            partition_name = f"partition_{user_id}"
            create_partition_if_not_exist_milvus(milvus_client, partition_name)

            # create user doc dir
            user_doc_dir = os.path.join(FILE_STORAGE_DIR, "user_" + user_id)
            os.makedirs(user_doc_dir, exist_ok=True)
        mongo_sess.end_session()
        response_data["detail"] = response_data.get("detail", f"registered user with id: {user_id} in db")
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", "failed to register user in db")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.delete("/{user_id}", response_model=Dict,
               status_code=status.HTTP_200_OK,
               summary="Unregisters the user with the given user_id")
async def unregister_user(user_id: str):
    """
    Unregisters the user with the given user_id.
    Warning, all user information, document, & vector entries will be lost
    """
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        mongo_sess = mongodb_client.start_session()
        with mongo_sess.start_transaction():  # atomic mongo transaction
            users = mongodb_client[MONGO_USER_DB][MONGO_USER_COLLECTION]
            user_query = {"_id": user_id}
            user = users.find_one(user_query)
            if not user:
                status_code = status.HTTP_404_NOT_FOUND
                response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
                raise HTTPException(status_code=status_code, detail=response_data["detail"])
            users.delete_one(user_query, session=mongo_sess)

            # delete all user documents in mongo documents collection
            docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]
            docs.delete_many({"user_id": user_id}, session=mongo_sess)

            # drop user partition in milvus
            partition_name = f"partition_{user_id}"
            # release  partition from memory
            milvus_client.partition(partition_name).release()
            milvus_client.drop_partition(partition_name)

            # delete user doc dir
            user_doc_dir = os.path.join(FILE_STORAGE_DIR, "user_" + user_id)
            shutil.rmtree(user_doc_dir)
        mongo_sess.end_session()
        response_data["detail"] = f"user with id {user_id} removed from db"
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", f"failed to unregister user with id {user_id}")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.delete("/{user_id}/documents/{doc_id}", response_model=Dict,
               status_code=status.HTTP_200_OK,
               summary="Deletes the document with the doc_id for the user with the given user_id")
async def delete_user_document(
        user_id: str,
        doc_id: str):
    """
    Deletes the document with the doc_id for the user with the given user_id
    Warning, user document & vector entry will be lost
    """
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        mongo_sess = mongodb_client.start_session()
        with mongo_sess.start_transaction():  # atomic mongo transaction
            if not user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
                status_code = status.HTTP_404_NOT_FOUND
                response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
                raise HTTPException(status_code=status_code, detail=response_data["detail"])

            docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]
            # find doc with matching doc_id
            doc = docs.find_one({"_id": doc_id})
            if not doc:
                status_code = status.HTTP_404_NOT_FOUND
                response_data["detail"] = f"doc with id: {doc_id} does not exist in db for user {user_id}."
                raise HTTPException(status_code=status_code, detail=response_data["detail"])

            # delete the doc matching doc_id
            docs.delete_one({"_id": doc_id}, session=mongo_sess)

            # delete all entities matching doc_id in user partition
            partition_name = f"partition_{user_id}"
            load_partition_milvus(milvus_client, partition_name)
            while True:
                query_res = milvus_client.query(
                    expr=f'user_id in ["{user_id}"]',
                    offset=0,
                    limit=10000,
                    output_fields=["doc_id"],
                    partition_names=[partition_name],
                    consistency_level="Strong")
                # break if all entities removed
                if not query_res:
                    break
                doc_entity_ids = [res["id"] for res in query_res]

                # delete all entities by PK id
                milvus_client.delete(
                    f"id in {doc_entity_ids}".replace("'", '"'),
                    partition_name=partition_name)

            # delete user doc from persistent storage
            os.remove(doc["doc_path"])
        mongo_sess.end_session()
        response_data["detail"] = f"doc with id {doc_id} removed for user with id {user_id}"
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", f"failed to delete doc with id {doc_id} for user with id {user_id}")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.delete("/{user_id}/documents", response_model=Dict,
               status_code=status.HTTP_200_OK,
               summary="Deletes all documents for the user with the given user_id")
async def delete_all_user_documents(
        user_id: str):
    """
    Deletes all documents for the user with the given user_id
    Warning, user document & vector entry will be lost
    """
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        mongo_sess = mongodb_client.start_session()
        with mongo_sess.start_transaction():  # atomic mongo transaction
            if not user_exists_in_mongo(mongodb_client, user_id, MONGO_USER_DB, MONGO_USER_COLLECTION):
                status_code = status.HTTP_404_NOT_FOUND
                response_data["detail"] = f"user with id: {user_id} does not exist in db. Register user first"
                raise HTTPException(status_code=status_code, detail=response_data["detail"])

            # delete all docs matching doc_id
            docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]
            docs.delete_many({"user_id": user_id}, session=mongo_sess)

            # delete all entities matching user_id in user partition i.e. drop all user doc entities
            partition_name = f"partition_{user_id}"
            load_partition_milvus(milvus_client, partition_name)
            while True:
                query_res = milvus_client.query(
                    expr=f'user_id in ["{user_id}"]',
                    offset=0,
                    limit=10000,
                    output_fields=["user_id"],
                    partition_names=[partition_name],
                    consistency_level="Strong")
                # break if all entities removed
                if not query_res:
                    break
                user_entity_ids = [res["id"] for res in query_res]

                # delete all entities by PK id
                milvus_client.delete(
                    f"id in {user_entity_ids}".replace("'", '"'),
                    partition_name=partition_name)

            # delete user doc dir
            user_doc_dir = os.path.join(FILE_STORAGE_DIR, "user_" + user_id)
            shutil.rmtree(user_doc_dir)
            # recreate user doc dir
            os.makedirs(user_doc_dir, exist_ok=True)
        mongo_sess.end_session()
        response_data["detail"] = f"deleted all documents for user with id: {user_id}"
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", f"failed to delete documents for user with id: {user_id}")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data


@router.delete("", response_model=Dict,
               status_code=status.HTTP_200_OK,
               summary="Deletes all users and related documents in system")
async def delete_all_users():
    """
    Deletes all users and related documents in system
    Warning, all user information and documents will be lost
    """
    status_code = status.HTTP_200_OK
    response_data = {}
    try:
        mongo_sess = mongodb_client.start_session()
        with mongo_sess.start_transaction():  # atomic mongo transaction
            # delete all users and docs in mongodb
            users = mongodb_client[MONGO_USER_DB][MONGO_USER_COLLECTION]
            docs = mongodb_client[MONGO_USER_DB][MONGO_DOC_COLLECTION]

            users.delete_many({}, session=mongo_sess)
            docs.delete_many({}, session=mongo_sess)

            # drop all milvus partitions in current collection
            milvus_client.release()
            for partition in milvus_client.partitions:
                milvus_client.drop_partition(partition)

            # delete user doc dir
            shutil.rmtree(FILE_STORAGE_DIR)
            # recreate empty user doc dir
            os.makedirs(FILE_STORAGE_DIR, exist_ok=True)

        mongo_sess.end_session()
        response_data["detail"] = "all users and docs removed from db"
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        status_code = status.HTTP_400_BAD_REQUEST if status_code == status.HTTP_200_OK else status_code
        detail = response_data.get("detail", "failed to unregister all users & delete docs from db")
        raise HTTPException(status_code=status_code, detail=detail) from excep
    return response_data
