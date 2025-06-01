#!/bin/bash
set -e

# Create directory for generated code
mkdir -p api/grpc/generated

# Generate Python code
python -m grpc_tools.protoc \
  -I./proto \
  --python_out=./api/grpc/generated \
  --grpc_python_out=./api/grpc/generated \
  ./proto/notes.proto

# Fix imports in generated files
sed -i '' 's/import notes_pb2/from api.grpc.generated import notes_pb2/g' api/grpc/generated/notes_pb2_grpc.py

# Create __init__.py files
touch api/grpc/generated/__init__.py
touch api/grpc/__init__.py

echo "gRPC code generation complete!" 