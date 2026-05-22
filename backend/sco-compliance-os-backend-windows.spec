# -*- mode: python ; coding: utf-8 -*-
# PyInstaller .spec per Windows.
# Entry point: backend/sco_compliance_os/main.py
# Pattern Conv. 44 lesson 3 enforcement: tutte le transitive deps dichiarate
# esplicitamente in hiddenimports (email_validator, dns.resolver, idna sono
# i casi noti che PyInstaller perde per dynamic load / meta-introspection).

import sys
from pathlib import Path

# Path entry point
ENTRY = Path("sco_compliance_os") / "main.py"

# Hidden imports: tutte le transitive che PyInstaller statico puo' perdere
hiddenimports = [
    # Claude Agent SDK + MCP
    "claude_agent_sdk",
    "mcp",
    "mcp.client",
    "mcp.server",
    "mcp.types",
    # Pydantic email validation chain (Conv. 44 lesson 3)
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
    # Keyring Windows backend
    "keyring",
    "keyring.backends",
    "keyring.backends.Windows",
    "win32cred",
    "win32ctypes",
    "win32ctypes.core",
    "win32ctypes.pywin32",
    # Sentry
    "sentry_sdk",
    "sentry_sdk.integrations",
    "sentry_sdk.integrations.fastapi",
    "sentry_sdk.integrations.starlette",
    "sentry_sdk.integrations.logging",
    # Uvicorn server
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
    # Google OAuth + API (Gmail/GCal/GDrive)
    "google",
    "google.auth",
    "google.auth.transport.requests",
    "google.oauth2",
    "google.oauth2.credentials",
    "google_auth_oauthlib",
    "google_auth_oauthlib.flow",
    "googleapiclient",
    "googleapiclient.discovery",
    "googleapiclient.errors",
    # Document parsing
    "pypdf",
    "docx",
    # TokenJuice
    "html2text",
    # SSE streaming
    "sse_starlette",
    # SQLAlchemy (transitive di alcune deps)
    "sqlalchemy",
    "sqlalchemy.ext.asyncio",
    "aiosqlite",
    # PyJWT (future license JWT)
    "jwt",
]

# File dati statici (config, prompt templates, asset)
datas = []

# Block cipher disabilitato per build pulito
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    upx=False,  # UPX puo' triggerare false positive AV su Windows
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI-mode, niente console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
