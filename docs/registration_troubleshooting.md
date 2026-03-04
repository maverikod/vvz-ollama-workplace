# Registration with proxy: why "Proxy not available"

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com  

When the adapter logs **"Proxy not available at https://mcp-proxy:3004"**, the framework treats the failure as a **connection-level** error (unreachable host, refused, or TLS handshake failure). The actual exception is not printed in that message. Below are the main causes and how to check them.

## Most likely cause: wrong CA for verifying the proxy (server)

**Observed:** TCP to `mcp-proxy:3004` works from the adapter container, but TLS fails with:

`SSLCertVerificationError: certificate verify failed: self-signed certificate in certificate chain`

**Reason:** For the **registration** connection the adapter is the **client** and the proxy is the **server**. The adapter must verify the **proxy’s server certificate** using the **CA that signed the proxy’s server cert** (proxy’s CA). If `registration.ssl.ca` points to **our** CA (e.g. `mtls_certificates/ca.crt`), we are verifying the proxy’s server cert with the wrong CA and verification fails.

**Fix:**

- Put the **proxy’s CA** (the one that signed the proxy’s server certificate) in a file, e.g. `mtls_certificates/proxy-ca.crt`.
- In the adapter config, set `registration.ssl.ca` to that path (e.g. `/app/certs/proxy-ca.crt`) so the adapter uses it **only** to verify the proxy’s server cert when connecting to the proxy.
- Keep using `client.crt` / `client.key` (signed by your CA) for client auth; the **proxy** must trust your CA to accept the adapter.

So: **registration.ssl.ca** = CA that signed the **proxy’s** server cert (to verify the proxy). **Client cert/key** = your adapter’s cert (proxy must trust your CA).

## 1. Proxy not reachable (host/port/network)

**Cause:** The adapter container cannot open a TCP connection to `mcp-proxy:3004`.

**Check:**

- Proxy is running and listening on port **3004** (e.g. inside its own container).
- Adapter and proxy are on the **same Docker network** (e.g. **smart-assistant**).  
  - From the adapter container:  
    `docker exec -it ollama-adapter sh -c "getent hosts mcp-proxy || echo 'mcp-proxy not resolved'"`  
  - If the name does not resolve or you get "Connection refused", fix the network or proxy hostname/port.
- If the proxy runs on the host, use the host’s IP or a network alias the container can resolve, and set `MCP_PROXY_HOST` accordingly (not `mcp-proxy` unless that name resolves inside the container).

## 2. Wrong proxy host/port

**Cause:** Config or env points to a host/port where no proxy is listening.

**Check:**

- In the adapter config, `registration.register_url` is `https://mcp-proxy:3004/register` (or whatever host/port the proxy uses).
- Env overrides: `MCP_PROXY_HOST`, `MCP_PROXY_PORT` (default 3004). If the proxy is on another host/port, set these when starting the adapter container.

## 3. mTLS: proxy does not accept the client certificate

**Cause:** The proxy requires client mTLS and does not trust the adapter’s client cert (or the adapter is not presenting it correctly).

**Check:**

- Adapter uses certs from **mtls_certificates/** (or the mounted dir): `ca.crt`, `client.crt`, `client.key`, `server.crt`, `server.key`.
- **Proxy is configured to trust the same CA** that signed `client.crt` (e.g. add `mtls_certificates/ca.crt` to the proxy’s client CA trust store).
- If the proxy uses its own CA, the adapter’s `client.crt`/`client.key` must be signed by that CA and the proxy must be configured to require and verify client certs with that CA.

## 4. See the real error (for debugging)

The message "Proxy not available" is shown when the framework classifies the exception as a connection error (e.g. `httpx.ConnectError` or message containing "connection" and "refused"/"failed"). The **underlying exception** is not shown in that line.

To see the real error:

- Set adapter **log level to DEBUG** in config (`server.log_level`: `"DEBUG"`) and check the logs for the exception or stack trace around the registration attempt.
- Or temporarily patch the environment so that Python logs full tracebacks (e.g. run with `PYTHONFAULTHANDLER=1` or increase logging verbosity) and reproduce the registration failure.

## Summary checklist

| Check | Action |
|-------|--------|
| Proxy listening | Proxy process runs and listens on 3004. |
| Same network | Adapter and proxy on same Docker network (e.g. `smart-assistant`). |
| Name resolution | From adapter container, `mcp-proxy` resolves (or use correct `MCP_PROXY_HOST`). |
| Port 3004 | Config/URL and env use port 3004 (or the proxy’s real port). |
| Client certs | `client.crt`/`client.key` present in mounted certs dir; config points to them. |
| Proxy trusts CA | Proxy’s client CA list includes the CA that signed `client.crt`. |
