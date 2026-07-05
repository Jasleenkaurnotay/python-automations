#!/bin/bash

# Create volume to copy library from container image
mkdir -p lambda-layer

# Create docker container > python library > export to local folder
docker run --rm \
    --mount type=bind,source="$(pwd)/lambda-layer",target=/layer \
    public.ecr.aws/sam/build-python3.13 \
    pip install psycopg2-binary -t /layer/python/lib/python3.13/site-packages/

# zip the local folder's content
cd "$(pwd)/lambda-layer"
zip -r layer.zip .

# Bring back control to the previous working directory
cd ..
