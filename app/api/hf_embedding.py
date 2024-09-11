"""
Huggingface api functions
"""
import os
import requests
from utils.common import timeit_decorator


DEBUG: bool = os.environ.get("DEBUG", "") != "False"


def query_api_online(payload: str, hf_api_tkn: str, hf_api_url: str, timeout: float = 30) -> dict:
    """
    Get embedding of the payload text using an online api endpoint
    Input sequence token length > 256 word pieces are truncated
    The following url returns a vector of length 384 and by default input text longer than 256 word pieces is truncated.
    https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2#:~:text=The%20sentence%20vector%20may%20be,256%20word%20pieces%20is%20truncated.
    """
    headers = {"Authorization": f"Bearer {hf_api_tkn}"}
    headers = {"accept": "application/json"}
    response = requests.post(hf_api_url, headers=headers, json=payload, timeout=timeout)
    return response.json()


def query_api_docker(payload: str, hf_api_url: str = "http://hf_text_embedding_api:8009/embedding/{text}", timeout: float = 30) -> dict:
    """
    Get embedding of the payload text using a dockerized api endpoint
    Input sequence token length > 256 word pieces are truncated
    The following url returns a vector of length 384 and by default input text longer than 256 word pieces is truncated.
    """
    # add query to hf_api_url
    hf_api_url += f"?query={payload}"
    headers = {"accept": "application/json"}
    response = requests.post(hf_api_url, headers=headers, data="", timeout=timeout)
    return response.json()["embedding"]


# if DEBUG is true, function runs are time
if DEBUG:
    query_api_online = timeit_decorator(query_api_online)
    query_api_docker = timeit_decorator(query_api_docker)


if __name__ == "__main__":
    import os
    HF_API_TOKEN = os.getenv("HF_API_TOKEN")
    HF_API_URL = os.getenv("HF_API_URL")

    # example use of a hf feature extraction pipeline with a dockerized hf api call
    embeddings = query_api_docker("Humans like dogs")
    print(len(embeddings))

    # example use of a hf feature extraction pipeline with an online hf api call
    eg_payload = {
        "inputs": [
            "Dogs are nice creatures",
            "Dogs are man's best friend",
            "Humans like dogs"
        ],
        "options": {"wait_for_model": True}
    }
    output = query_api_online(eg_payload, HF_API_TOKEN, HF_API_URL)
    print("len(output) = ", len(output))
    print("len(output[0]) / length of embedding = ", len(output[0]))

    # example of feature extraction pipeline with a locally hosted model
    from sentence_transformers import SentenceTransformer
    sentences = ["Humans like dogs"]

    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    embeddings = model.encode(sentences)
    print(embeddings.shape)
