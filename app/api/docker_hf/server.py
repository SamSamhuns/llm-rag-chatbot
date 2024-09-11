"""
fastapi setup with huggingface feature extraction api exposed
"""
import logging
import argparse
import traceback

import uvicorn
from fastapi import FastAPI, status, HTTPException
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

app = FastAPI()
feature_ext = SentenceTransformer(MODEL_NAME)
logger = logging.getLogger('hf_emb_server_api')


@app.get("/")
def read_root():
    """
    welcome message
    """
    return {"Welcome to a docker hosted huggingface api. Navigate to /docs"}


@app.post("/embedding/{text}", status_code=status.HTTP_200_OK,)
def get_embedding(query: str):
    """
    Get query text embedding
    """
    response_data = {}
    try:
        embedding = feature_ext.encode(query)
        response_data["detail"] = "embeddings extracted"
        response_data["embedding"] = embedding.tolist()
    except Exception as excep:
        logger.error("%s: %s", excep, traceback.print_exc())
        detail = response_data.get("detail", "failed to get text embeddings")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST , detail=detail) from excep
    return response_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        """Start FastAPI with uvicorn server hosting inference models""")
    parser.add_argument('-ip', '--host_ip', type=str, default="0.0.0.0",
                        help='host ip address. (default: %(default)s)')
    parser.add_argument('-p', '--port', type=int, default=8009,
                        help='uvicorn port number. (default: %(default)s)')
    parser.add_argument('-w', '--workers', type=int, default=1,
                        help="number of uvicorn workers. (default: %(default)s)")
    args = parser.parse_args()

    logger.info("Uvicorn server running on %s:%s with %s workers",
                args.host_ip, args.port, args.workers)
    uvicorn.run("server:app", host=args.host_ip, port=args.port,
                workers=args.workers, reload=True)
