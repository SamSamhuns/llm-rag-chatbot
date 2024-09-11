import pytest


@pytest.mark.asyncio
@pytest.mark.order(after=["test_upsert.py::test_upsert_file_txt"])
async def test_search_existing(test_app_asyncio, test_mongodb_conn, test_milvus_conn, mock_user_data_dict):

    user_data = mock_user_data_dict()
    param_dict = {"query": "cuda devices"}

    response = await test_app_asyncio.post(
        f"/qa/{user_data['user_id']}",
        params=param_dict)
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response['content']) == 8


@pytest.mark.asyncio
@pytest.mark.order(after=["test_upsert.py::test_upsert_file_txt"])
async def test_search_non_existing(test_app_asyncio, test_mongodb_conn, test_milvus_conn, mock_user_data_dict):

    user_data = mock_user_data_dict()
    param_dict = {"query": "cuda devices",
                  "doc_id_list": ["x"]}

    response = await test_app_asyncio.post(
        f"/qa/{user_data['user_id']}",
        params=param_dict)
    assert response.status_code == 200
    json_response = response.json()
    assert "content" not in json_response
