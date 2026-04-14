"""
MCPGuard Test MCP Server
========================
A realistic MCP server with 10 tools designed to test every rule
combination in MCPGuard.

Tools:
  1. bash_execute        — runs shell commands (dangerous, tests rm/force rules)
  2. db_query            — executes SQL queries (tests DROP/TRUNCATE rules)
  3. file_read           — reads a file by path (read-only, safe)
  4. file_write          — writes content to a file (write operation)
  5. file_delete         — deletes a file (destructive)
  6. list_directory      — lists files in a directory (read-only)
  7. get_environment     — returns env vars by key (read, potentially sensitive)
  8. send_http_request   — makes an HTTP request to a URL (write/external)
  9. search_records      — searches a mock database (read-only)
  10. delete_records     — deletes records from mock database (destructive)

Authentication:
  Bearer token in Authorization header.
  Token: "test-secret-token-mcpguard-2026"
  Set in .env or hardcoded here for testing.

Run:
  pip install fastmcp python-dotenv
  python test_mcp_server.py

Server runs at: http://localhost:8000/mcp
"""

import os
import json
import subprocess
from typing import Optional
from fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────

# Simple static token auth — in production use RSA/JWT
# For testing we use a custom middleware approach since FastMCP 2.x
# supports auth via dependencies

SERVER_TOKEN = os.getenv("MCP_SERVER_TOKEN", "eyi09kfstuvwxyz001223jdkendhwtebduqj3882ndheqjeuw73hjewubUBvc")
PORT = int(os.getenv("MCP_SERVER_PORT", "8000"))

# Mock database — in-memory for testing
_mock_db: list[dict] = [
    {"id": 1, "name": "Alice",   "email": "alice@example.com",   "role": "admin"},
    {"id": 2, "name": "Bob",     "email": "bob@example.com",     "role": "user"},
    {"id": 3, "name": "Charlie", "email": "charlie@example.com", "role": "user"},
    {"id": 4, "name": "Diana",   "email": "diana@example.com",   "role": "moderator"},
    {"id": 5, "name": "Eve",     "email": "eve@example.com",     "role": "user"},
]

# ── FastMCP app ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="MCPGuard Test Server",
    instructions=(
        "A test MCP server for MCPGuard rule engine testing. "
        "Contains tools ranging from safe reads to destructive operations."
    ),
)


# ── Tool 1: bash_execute ──────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Execute a shell command on the server. "
        "Supports any bash command. Use with caution — destructive commands "
        "like rm, mkfs, or force-push are irreversible."
    )
)
def bash_execute(command: str, working_directory: Optional[str] = None) -> dict:
    """
    Execute a shell command.

    Args:
        command: The shell command to run.
        working_directory: Optional directory to run the command in.

    Returns:
        stdout, stderr, and exit code.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=working_directory,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 10 seconds", "command": command}
    except Exception as e:
        return {"error": str(e), "command": command}


# ── Tool 2: db_query ──────────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Execute a SQL-like query against the database. "
        "Supports SELECT, INSERT, UPDATE, DELETE, DROP, and TRUNCATE operations. "
        "WARNING: DROP and TRUNCATE are irreversible."
    )
)
def db_query(query: str, database: str = "main") -> dict:
    """
    Execute a database query.

    Args:
        query: The SQL query to execute.
        database: The target database name.

    Returns:
        Query results or affected row count.
    """
    q = query.strip().upper()

    if q.startswith("SELECT"):
        return {
            "rows": _mock_db,
            "count": len(_mock_db),
            "query": query,
            "database": database,
        }
    elif q.startswith("DROP"):
        return {
            "result": f"Table dropped in database '{database}'",
            "query": query,
            "affected_rows": len(_mock_db),
        }
    elif q.startswith("TRUNCATE"):
        return {
            "result": f"Table truncated in database '{database}'",
            "query": query,
            "affected_rows": len(_mock_db),
        }
    elif q.startswith("DELETE"):
        return {
            "result": "Rows deleted",
            "query": query,
            "affected_rows": 2,
        }
    elif q.startswith("INSERT"):
        return {
            "result": "Row inserted",
            "query": query,
            "affected_rows": 1,
        }
    elif q.startswith("UPDATE"):
        return {
            "result": "Rows updated",
            "query": query,
            "affected_rows": 1,
        }
    else:
        return {"error": f"Unsupported query type: {query[:20]}", "query": query}


# ── Tool 3: file_read ─────────────────────────────────────────────────────────

@mcp.tool(
    description="Read the contents of a file at the given path. Safe read-only operation."
)
def file_read(path: str, encoding: str = "utf-8") -> dict:
    """
    Read a file's contents.

    Args:
        path: Absolute or relative path to the file.
        encoding: File encoding (default utf-8).

    Returns:
        File contents and metadata.
    """
    try:
        with open(path, "r", encoding=encoding) as f:
            content = f.read()
        return {
            "path": path,
            "content": content,
            "size_bytes": len(content.encode(encoding)),
            "encoding": encoding,
        }
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as e:
        return {"error": str(e), "path": path}


# ── Tool 4: file_write ────────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Write content to a file. Creates the file if it does not exist, "
        "overwrites if it does. This is a write operation."
    )
)
def file_write(path: str, content: str, encoding: str = "utf-8") -> dict:
    """
    Write content to a file.

    Args:
        path: Path to write to.
        content: Content to write.
        encoding: File encoding.

    Returns:
        Success status and bytes written.
    """
    try:
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        return {
            "path": path,
            "bytes_written": len(content.encode(encoding)),
            "success": True,
        }
    except Exception as e:
        return {"error": str(e), "path": path}


# ── Tool 5: file_delete ───────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Permanently delete a file at the given path. "
        "This operation is irreversible. DESTRUCTIVE."
    )
)
def file_delete(path: str, confirm: bool = False) -> dict:
    """
    Delete a file permanently.

    Args:
        path: Path to the file to delete.
        confirm: Must be True to proceed (safety check).

    Returns:
        Success status.
    """
    if not confirm:
        return {"error": "Set confirm=true to proceed with deletion", "path": path}
    try:
        os.remove(path)
        return {"path": path, "deleted": True}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except Exception as e:
        return {"error": str(e), "path": path}


# ── Tool 6: list_directory ────────────────────────────────────────────────────

@mcp.tool(
    description="List files and directories at the given path. Safe read-only operation."
)
def list_directory(path: str = ".", show_hidden: bool = False) -> dict:
    """
    List contents of a directory.

    Args:
        path: Directory path (default: current directory).
        show_hidden: Whether to include hidden files.

    Returns:
        List of files and directories.
    """
    try:
        entries = os.listdir(path)
        if not show_hidden:
            entries = [e for e in entries if not e.startswith(".")]
        entries.sort()
        return {
            "path": path,
            "entries": entries,
            "count": len(entries),
        }
    except Exception as e:
        return {"error": str(e), "path": path}


# ── Tool 7: get_environment ───────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Retrieve environment variable values by key. "
        "Can expose sensitive configuration — use carefully."
    )
)
def get_environment(key: str, default: Optional[str] = None) -> dict:
    """
    Get an environment variable value.

    Args:
        key: The environment variable name.
        default: Value to return if the key is not set.

    Returns:
        The variable value or default.
    """
    value = os.getenv(key, default)
    return {
        "key": key,
        "value": value,
        "found": key in os.environ,
    }


# ── Tool 8: send_http_request ─────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Send an HTTP request to an external URL. "
        "Supports GET, POST, PUT, DELETE methods. "
        "Can exfiltrate data if used carelessly."
    )
)
def send_http_request(
    url: str,
    method: str = "GET",
    body: Optional[str] = None,
    headers: Optional[dict] = None,
) -> dict:
    """
    Make an HTTP request to an external URL.

    Args:
        url: The target URL.
        method: HTTP method (GET, POST, PUT, DELETE).
        body: Request body for POST/PUT.
        headers: Additional headers.

    Returns:
        Response status and body.
    """
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(
            url,
            data=body.encode() if body else None,
            headers=headers or {},
            method=method.upper(),
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {
                "url": url,
                "method": method,
                "status_code": resp.status,
                "body": resp.read(2048).decode("utf-8", errors="replace"),
            }
    except urllib.error.HTTPError as e:
        return {"url": url, "status_code": e.code, "error": str(e)}
    except Exception as e:
        return {"url": url, "error": str(e)}


# ── Tool 9: search_records ────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Search records in the database by name, email, or role. "
        "Read-only operation — does not modify any data."
    )
)
def search_records(
    query: str,
    field: str = "name",
    limit: int = 10,
) -> dict:
    """
    Search records by a field value.

    Args:
        query: Search string (case-insensitive substring match).
        field: Field to search in — name, email, or role.
        limit: Maximum results to return.

    Returns:
        Matching records.
    """
    if field not in ("name", "email", "role"):
        return {"error": f"Invalid field '{field}'. Use name, email, or role."}

    results = [
        r for r in _mock_db
        if query.lower() in str(r.get(field, "")).lower()
    ][:limit]

    return {
        "query": query,
        "field": field,
        "results": results,
        "count": len(results),
    }


# ── Tool 10: delete_records ───────────────────────────────────────────────────

@mcp.tool(
    description=(
        "Permanently delete records from the database by ID or field value. "
        "This operation is irreversible. DESTRUCTIVE."
    )
)
def delete_records(
    field: str,
    value: str,
    database: str = "main",
) -> dict:
    """
    Delete records matching a field/value pair.

    Args:
        field: Field to match on (id, name, email, role).
        value: Value to match.
        database: Target database.

    Returns:
        Number of records deleted.
    """
    global _mock_db

    if field not in ("id", "name", "email", "role"):
        return {"error": f"Invalid field '{field}'"}

    before = len(_mock_db)
    _mock_db = [
        r for r in _mock_db
        if str(r.get(field, "")) != str(value)
    ]
    deleted = before - len(_mock_db)

    return {
        "field": field,
        "value": value,
        "database": database,
        "deleted_count": deleted,
        "remaining": len(_mock_db),
    }


# ── Auth middleware ───────────────────────────────────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """
    Validates the Authorization: Bearer <token> header on all requests.
    Returns 401 if missing or invalid.
    Skips auth for the root path (health check).
    """
    async def dispatch(self, request: StarletteRequest, call_next):
        if request.url.path == "/":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Missing Authorization header"},
            )

        token = auth_header[7:].strip()
        if token != SERVER_TOKEN:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid token"},
            )

        return await call_next(request)


# ── Mount middleware and run ──────────────────────────────────────────────────

# Get the underlying Starlette app from FastMCP and add middleware
http_app = mcp.http_app(transport="streamable-http")
http_app.add_middleware(BearerTokenMiddleware)


if __name__ == "__main__":
    import uvicorn

    print(f"""
╔══════════════════════════════════════════════════════╗
║         MCPGuard Test MCP Server                     ║
╠══════════════════════════════════════════════════════╣
║  URL:    http://localhost:{PORT}/mcp                    ║
║  Token:  {SERVER_TOKEN[:20]}...  ║
║  Tools:  10                                          ║
╠══════════════════════════════════════════════════════╣
║  Register in MCPGuard:                               ║
║  URL → http://localhost:{PORT}/mcp                      ║
║  Auth → Bearer {SERVER_TOKEN[:20]}...  ║
╚══════════════════════════════════════════════════════╝
    """)

    uvicorn.run(http_app, host="0.0.0.0", port=PORT)