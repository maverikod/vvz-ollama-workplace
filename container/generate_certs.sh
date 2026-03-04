#!/bin/sh
# Generate CA, server cert, and client cert for mTLS (adapter + registration).
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

set -e
CERTS_DIR="${1:-/app/certs}"
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -out ca.crt \
  -subj "/CN=ollama-workstation-ca"

# Server cert (adapter)
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/CN=ollama-workstation"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 3650 -sha256
rm -f server.csr

# Client cert (for registration to proxy)
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
  -subj "/CN=ollama-workstation-client"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out client.crt -days 3650 -sha256
rm -f client.csr

echo "Generated CA, server and client certs in $CERTS_DIR"
