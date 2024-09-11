import pytest


@pytest.mark.asyncio
@pytest.mark.order(after=["test_users.py::test_delete_user"])
async def test_upsert_file_txt(test_app_asyncio, test_mongodb_conn, test_milvus_conn, mock_txt_file, mock_user_data_dict):

    user_data = mock_user_data_dict()
    # create user with the corresponding data
    await test_app_asyncio.post("/users", params=user_data)

    fpath, fcontent = mock_txt_file
    files = {'files': (fpath, fcontent, 'text/plain')}

    response = await test_app_asyncio.post(
        f"/upsert/files/{user_data['user_id']}",
        files=files)
    assert response.status_code == 200
    json_response = response.json()
