# Chatbot Backend

Backend with fastapi+uvicorn for omni chat.

- [Chatbot Backend](#chatbot-backend)
  - [Setup](#setup)
    - [1. Create .env file](#1-create-env-file)
    - [2. Create shared volumes directory](#2-create-shared-volumes-directory)
    - [3. Create keyfile for mongo partition security](#3-create-keyfile-for-mongo-partition-security)
      - [Note:](#note)
    - [Docker Compose Setup for Deployment](#docker-compose-setup-for-deployment)
    - [Local Setup for Development](#local-setup-for-development)
      - [i) Uvicorn server with fastapi with Docker](#i-uvicorn-server-with-fastapi-with-docker)
      - [Or, ii) Uvicorn server with fastapi in local system](#or-ii-uvicorn-server-with-fastapi-in-local-system)
      - [Optionally expose app through ngrok docker for sharing localhost on the internet](#optionally-expose-app-through-ngrok-docker-for-sharing-localhost-on-the-internet)
  - [Testing](#testing)
  - [TODO](#todo)
  - [Chat completion endpoint with fschat Vicuna 13B](#chat-completion-endpoint-with-fschat-vicuna-13b)
    - [Download llama models](#download-llama-models)
    - [Convert llama model to hf format](#convert-llama-model-to-hf-format)
    - [Convert llama hf model to vicuna model](#convert-llama-hf-model-to-vicuna-model)
    - [To run the Vicuna model in the terminal as an interactive CLI session](#to-run-the-vicuna-model-in-the-terminal-as-an-interactive-cli-session)
    - [To run the Vicuna model as a fastapi endpoint server compatible with the openai API](#to-run-the-vicuna-model-as-a-fastapi-endpoint-server-compatible-with-the-openai-api)
    - [Notes on LLM RAG](#notes-on-llm-rag)


## Setup

### 1. Create .env file

Create a `.env` file in the same directory as the `docker-compose.yml` file with the following keys with updated values for unames and pass:

```yaml
# set to False for deployment
DEBUG=True
# http api server
API_SERVER_PORT=8080
# milvus
MILVUS_HOST=standalone
MILVUS_PORT=19530
ATTU_PORT=3000
# mongodb
MONGO_HOST=mongod1
MONGO_PORT=27017
MONGO_INITDB_ROOT_USERNAME=root
MONGO_INITDB_ROOT_PASSWORD=admin
MONGO_USER_DB=user_db
MONGO_USER_COLLECTION=users
MONGO_DOC_COLLECTION=docs
# mongo express
MONGOEXP_PORT=8081
MONGOEXP_USERNAME=admin
MONGOEXP_PASSWORD=admin
# redis
REDIS_HOST=redis-server
REDIS_PORT=6379
# huggingface
HF_API_TOKEN=<HUGGINGFACE_API_KEY>
HF_API_URL=<HUGGINGFACE_API_URL_ENDPOINT>
```

### 2. Create shared volumes directory

```shell
mkdir -p volumes/chatbot_backend
```

### 3. Create keyfile for mongo partition security

```shell
mkdir -p .docker/mongo/replica.key
openssl rand -base64 756 > .docker/mongo/replica.key
chmod 400 .docker/mongo/replica.key
```

#### Note:

When changing settings in `docker-compose.yml` for the mongodb service, the existing docker and shared volumes might have to be purged i.e. when changing replicaset name.

<p style="color:red;">WARNING: This will delete all existing user, document, and vector records.</p> 

```shell
docker-compose down
docker volume rm $(docker volume ls -q)
rm -rf volumes
```

### Docker Compose Setup for Deployment

Note: some services are set to bind to all addresses which should be changed in a production environment.

```shell
# build all required containers
docker-compose build
# start all services
docker-compose up -d
```

The server will be available at <http://localhost:8080> if using the default port.

### Local Setup for Development

Start all background database and other required services.

```shell
# build all required containers
docker-compose build
docker-compose up -d hf_text_embedding_api etcd minio standalone attu mongod1 mongo-setup mongo-express
```

Then use either i) Docker or ii) a local system setup to start the uvicorn+fastapi server.

#### i) Uvicorn server with fastapi with Docker

Build server container

```shell
bash scripts/build_docker.sh
```

Start server at HTTP port EXPOSED_HTTP_PORT

```shell
bash scripts/run_docker.sh -p EXPOSED_HTTP_PORT
```

The server will be available at <http://localhost:8080> if using the default port.

#### Or, ii) Uvicorn server with fastapi in local system

To properly resolve host-names in `.env`, the container service names in `docker-compose.yml` following must be added to `/etc/hosts` in the local system. This is not required when the fastapi-server is running inside a docker container.

```shell
127.0.0.1  mongod1
127.0.0.1  standalone
127.0.0.1  redis-server
127.0.0.1  hf_text_embedding_api
```

Install requirements inside venv or conda environment

```shell
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start server at HTTP port EXPOSED_HTTP_PORT. Note the host names must contain addresses when using docker microservices and the fastapi+uvicorn server outside the docker-compose environment.

```shell
python app/server.py -p EXPOSED_HTTP_PORT
```

The server will be available at <http://localhost:8080> if using the default port.

#### Optionally expose app through ngrok docker for sharing localhost on the internet

WARNING: Never use for production

```bash
# start chatbot-backend with python
# sign up for ngrok account at https://ngrok.com/
# https://ngrok.com/docs/using-ngrok-with/docker/
docker pull ngrok/ngrok
# for linux systems
docker run --net=host -it -e NGROK_AUTHTOKEN=<NGROK_AUTHTOKEN> ngrok/ngrok:latest http <EXPOSED_HTTP_PORT>
# for MacOS and windows
docker run -it -e NGROK_AUTHTOKEN=<NGROK_AUTHTOKEN> ngrok/ngrok:latest http host.docker.internal:<EXPOSED_HTTP_PORT>
```

## Testing

Note: all the microservices must already be running with docker-compose.

Install requirements:

```shell
pip install -r tests/requirements.txt
```

Run tests:

```shell
pytest tests/
```

Generating coverage reports

```shell
coverage run -m pytest tests/
coverage report -m -i
```

## TODO

-   Fix vector database to use
-   Use redis for caching if possible

## Chat completion endpoint with fschat Vicuna 13B

Use fastchat's API which can use OpenAI-compatible RESTful APIs
Vicuna can be used as a drop-in replacement

Vicuna README: <https://github.com/lm-sys/FastChat/tree/main>

### Download llama models 

Instructions from <https://huggingface.co/docs/transformers/main/model_doc/llama>

### Convert llama model to hf format

<https://huggingface.co/docs/transformers/main/model_doc/llama>

```shell
python convert_llama_weights_to_hf.py \
    --input_dir /home/mluser/sam/llama/weights --model_size 13B --output_dir llama13b
```

### Convert llama hf model to vicuna model

```shell
python3 -m fastchat.model.apply_delta \
    --base-model-path llama13b \
    --target-model-path vicuna-13b \
    --delta-path lmsys/vicuna-13b-delta-v1.1
```

### To run the Vicuna model in the terminal as an interactive CLI session

```shell
# for the fastchat t5 model
python3 -m fastchat.serve.cli --model-path lmsys/fastchat-t5-3b-v1.0
# or for the vicuna 13b model
python3 -m fastchat.serve.cli --model-path vicuna-13b
```

### To run the Vicuna model as a fastapi endpoint server compatible with the openai API

Launch the controller:

```shell
python3 -m fastchat.serve.controller
```

This controller manages the distributed workers:

Launch the model worker(s)
```shell
python -m fastchat.serve.model_worker --model-path=vicuna-13b
```

Run fastchat fastapi server with openai compatible apis:

```shell
python3 -m fastchat.serve.openai_api_server --port=8002
```

### Notes on LLM RAG

-   1. What You Put in the DB Really Impacts Performance

Document retrieval is very sensitive to noise. Obviously if you are missing important documents, your model can't answer from context. But if you just dump all of your docs in, you can end up handing documents as context that technically have some semantic content that sounds relevant, but is not helpful. Outdated policy or very obscure/corner case technical docs can be a problem. E.g., if there is this really random doc on changing spark plugs underwater, then when the user asks about vehicle maintenance the final answer might include information about scuba gear, underwater grounding, etc. that makes for a bad answer.

-   2. It's Hard to Get Models to Shut Up When There's No Context

In theory these things should NOT give answer if there's no relevant context--that's the whole point. The default prompt for QA in llama-index is

DEFAULT_TEXT_QA_PROMPT_TMPL = (
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context information and not prior knowledge, "
    "answer the query.\n"
    "Query: {query_str}\n"
    "Answer: "
)
That being said, if you ask dumbass questions like "Who won the 1976 Super Bowl?" or "What's a good recipe for a margarita?" it would cheerfully respond with an answer. We had to experiment for days to get a prompt that forced these darn models to only answer from context and otherwise say "There's no relevant information and so I can't answer."

-   3. Never use openAI embeddings for RAG. Use local embeddings, in MTEB benchmarks they do much better than openAI’s embeddings. If you are ok with sending your document to openAI (not concerned with privacy) better send the search query and locally searched few chunks of data to GPT-4 rather than sending whole dataset and the query (for tokenizing) to OpenAI for embedding. Also, if they no longer support tokenizing using text-embedding-ada-002 like they did with text-embedding-ada-001 recently, your local database is paperweight. You get the best of embeddings with local embedding and the best of AI with GPT-4 if you had done the reverse.

-   4. Don’t JUST use semantic search using cosine similarity using embeddings. I found that it doesn’t work in edge cases. What works better is selecting 4 chunks from embedding search and 4 chunks from good old lexical search (bm25+). It performs very well.

-   5. Sending one chunk on each side of selected chunks to provide more context works better.

-   6. Telling the GPT-4 in system message that sometimes it will get unrelated chunks, it can safely ignore them also helps.

-   7. Telling it to answer the question based on own data, with explicit disclaimer that it is not in the passages also helps the user get better answers overall.

-   8. If you must use local llm, try the largest llama-2 you can use but stick to textbook prompt mentioned in the repo. (The [inst] <<sys>> system message <</sys>> instruction [/inst] one) It works like gpt-3.5 or slightly better for RAG.
