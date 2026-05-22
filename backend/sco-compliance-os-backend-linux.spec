# -*- mode: python ; coding: utf-8 -*-
# PyInstaller .spec per Linux.
# Entry point: backend/sco_compliance_os/main.py
# Target: x86_64-unknown-linux-gnu.
# Conv. 44 lesson 3 enforcement: tutte transitive deps dichiarate.

from pathlib import Path

ENTRY = Path("sco_compliance_os") / "main.py"

hiddenimports = [
    # Claude Agent SDK + MCP
    "claude_agent_sdk",
    "mcp",
    "mcp.client",
    "mcp.server",
    "mcp.types",
    # Pydantic email validation chain
    "email_validator",
    "dns",
    "dns.resolver",
    "dns.rdatatype",
    "dns.rdataclass",
    "idna",
    # HTTP
    "httpx",
    "httpx._transports.default",
    "httpcore",
    "anyio",
    "h11",
    # Token counting
    "tiktoken",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
    # Crittografia
    "cryptography",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.bindings._rust",
    # Keyring Linux backend (Secret Service via dbus)
    "keyring",
    "keyring.backends",
    "keyring.backends.SecretService",
    "keyring.backends.libsecret",
    "secretstorage",
    "jeepney",
    "jeepney.io",
    "jeepney.io.blocking",
    # Sentry
    "sentry_sdk",
    "sentry_sdk.integrations",
    "sentry_sdk.integrations.fastapi",
    "sentry_sdk.integrations.starlette",
    "sentry_sdk.integrations.logging",
    # Uvicorn
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # Google OAuth + API
    "google", "google.auth", "google.auth.transport.requests",
    "google.oauth2", "google.oauth2.credentials",
    "google_auth_oauthlib", "google_auth_oauthlib.flow",
    "googleapiclient", "googleapiclient.discovery", "googleapiclient.errors",
    # Document parsing
    "pypdf", "docx",
    # TokenJuice
    "html2text",
    # SSE streaming
    "sse_starlette",
    # SQLAlchemy + aiosqlite
    "sqlalchemy", "sqlalchemy.ext.asyncio", "aiosqlite",
    # PyJWT
    "jwt",
]

datas = []
block_cipher = None

a = Analysis(
    [str(ENTRY)],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "jupyter",
        "pytest",
        "mypy",
        "ruff",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="sco-compliance-os-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
