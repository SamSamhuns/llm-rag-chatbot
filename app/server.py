"""
Main fastapi server file

This file contains the main FastAPI server setup. It:
- Creates the FastAPI app
- Adds middleware (CORS, timing)
- Mounts static files
- Includes API routers
- Defines an OpenAPI schema
- Starts a Uvicorn server

Args:
    cfg (module): Configuration variables
    users (module): Users API router
    upsert (module): Upsert API router
    search (module): Search API router
    qa (module): QA API router

Returns:
    app (FastAPI): The FastAPI application object
"""
import os
import time
import argparse
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import config as cfg
from routes import users, upsert, search, qa


# openai app
def get_application():
    """Returns a FastAPI app object.  

    Returns:
        app (FastAPI): A FastAPI app object.
    """
    app = FastAPI(title=cfg.PROJECT_NAME,
                  description=cfg.PROJECT_DESCRIPTION,
                  debug=cfg.DEBUG,
                  version=cfg.VERSION)
    app.mount("/static", StaticFiles(directory="./app/static"), name="static")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


# Docs
def custom_openapi():
    """Returns the OpenAPI schema for the FastAPI app.

    Returns:
        openapi_schema (dict): The OpenAPI schema.
    """
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=cfg.PROJECT_NAME,
        version=cfg.VERSION,
        description=cfg.PROJECT_DESCRIPTION,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# logging
logger = logging.getLogger("chatbot_backend_server")

# Routing
app = get_application()
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(upsert.router, prefix="/upsert", tags=["upsert"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(qa.router, prefix="/qa", tags=["qa"])
app.openapi = custom_openapi


# api call time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Adds an X-Process-Time header with the time taken to process the request.

    Args:
        request (Request): The request object.
        call_next (coroutine): The next middleware or endpoint.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/")
async def index():
    """Returns a welcome message."""
    return {"Welcome to the Omni ChatBot service": "Please visit /docs for list of apis"}


@app.get('/favicon.ico')
async def favicon():
    """Returns the favicon.ico file."""
    file_name = "favicon.ico"
    file_path = os.path.join(app.root_path, "app/static", file_name)
    return FileResponse(path=file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        """Start FastAPI with uvicorn server hosting inference models""")
    parser.add_argument('--ip', '--host_ip', dest="host_ip", type=str, default="0.0.0.0",
                        help='host ip address. (default: %(default)s)')
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='uvicorn port number. (default: %(default)s)')
    parser.add_argument('-w', '--workers', type=int, default=1,
                        help="number of uvicorn workers. (default: %(default)s)")
    parser.add_argument('-r', '--reload', action='store_true',
                        help="reload based on reload dir. (default: %(default)s)")
    args = parser.parse_args()
    args.reload = False if args.workers > 1 else args.reload

    logger.info("Uvicorn server running on %s:%s with %s workers", args.host_ip, args.port, args.workers)
    uvicorn.run("server:app", host=args.host_ip, port=args.port,
                workers=args.workers, reload=args.reload, reload_dirs=['app'])
