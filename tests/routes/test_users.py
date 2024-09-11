"""
Test user routes
"""
import copy
import pytest


# user registration, creation test

@pytest.mark.asyncio
async def test_post_new_user(test_app_asyncio, test_mongodb_conn, mock_user_data_dict):
    user_data = mock_user_data_dict()
    response = await test_app_asyncio.post("/users", params=user_data)
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.order(after="test_post_new_user")
async def test_post_repeated_user(test_app_asyncio, test_mongodb_conn, mock_user_data_dict):
    user_data = mock_user_data_dict()
    response = await test_app_asyncio.post("/users", params=user_data)
    assert response.status_code == 400


@pytest.mark.asyncio
@pytest.mark.order(after="test_post_new_user")
async def test_get_user_by_id(test_app_asyncio, mock_user_data_dict):
    user_data = mock_user_data_dict()
    response = await test_app_asyncio.get(f"/users/{user_data['user_id']}")
    assert response.status_code == 200

    user_data["_id"] = user_data.pop("user_id")
    user_data["name"] = user_data.pop("user_name")
    user_data["email"] = user_data.pop("user_email")
    assert response.json()["content"] == user_data


@pytest.mark.asyncio
@pytest.mark.order(after="test_post_new_user")
async def test_get_all_registered_user(test_app_asyncio, test_mongodb_conn, mock_user_data_dict):
    response = await test_app_asyncio.get("/users")
    assert response.status_code == 200
    users_list = response.json()["content"]

    user_data = mock_user_data_dict()
    user_data["_id"] = user_data.pop("user_id")
    user_data["name"] = user_data.pop("user_name")
    user_data["email"] = user_data.pop("user_email")
    assert users_list == [user_data]


@pytest.mark.asyncio
async def test_get_non_existent_user(test_app_asyncio, test_mongodb_conn):
    user_id = 999
    response = await test_app_asyncio.get(f"/users/{user_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.order(after=["test_get_user_by_id", "test_get_all_registered_user"])
async def test_delete_user(test_app_asyncio, test_mongodb_conn, mock_user_data_dict):
    user_data = mock_user_data_dict()
    response = await test_app_asyncio.delete(f"/users/{user_data['user_id']}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_non_existent_user(test_app_asyncio):
    user_id = 999
    response = await test_app_asyncio.delete(f"/users/{user_id}")
    assert response.status_code == 404


# user document tests


@pytest.mark.asyncio
@pytest.mark.order(after="test_post_new_user")
async def test_get_registered_user_all_docs(test_app_asyncio, test_mongodb_conn, mock_user_data_dict):
    user_data = mock_user_data_dict()
    response = await test_app_asyncio.get(f"/users/{user_data['user_id']}/documents")
    assert response.status_code == 200
    assert len(response.json()["content"]) == 1


@pytest.mark.asyncio
@pytest.mark.order(after="test_get_registered_user_all_docs")
async def test_get_registered_user_one_doc(test_app_asyncio, test_mongodb_conn, mock_user_data_dict):
    user_data = mock_user_data_dict()
    response = await test_app_asyncio.get(f"/users/{user_data['user_id']}/documents")
    assert response.status_code == 200
    assert len(response.json()["content"]) == 1
    doc_id = response.json()["content"][0]["_id"]
    response = await test_app_asyncio.get(f"/users/{user_data['user_id']}/documents/{doc_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.order(after="test_get_registered_user_all_docs")
async def test_delete_user_one_doc(test_app_asyncio, test_mongodb_conn, mock_user_data_dict):
    user_data = mock_user_data_dict()
    response = await test_app_asyncio.get(f"/users/{user_data['user_id']}/documents")
    assert response.status_code == 200
    assert len(response.json()["content"]) == 1
    doc_id = response.json()["content"][0]["_id"]
    response = await test_app_asyncio.get(f"/users/{user_data['user_id']}/documents/{doc_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_non_existent_user_doc(test_app_asyncio, test_mongodb_conn):
    user_id = 999
    response = await test_app_asyncio.get(f"/users/{user_id}/documents")
    assert response.status_code == 404
