#!/bin/bash
docker build -t chatbot_backend:latest --build-arg UID=$(id -u) .
