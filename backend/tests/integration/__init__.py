"""Integration tests for SCO Compliance OS backend.

Conv. 46 enforcement: smoke E2E test framework for autotest pre-tag.
Subagent DEV-AUTOTEST-E2E v0.7.0 24/05/2026.

Stack:
    - pytest + pytest-asyncio (asyncio_mode = auto da pyproject.toml)
    - httpx AsyncClient via ASGITransport (no real network)
    - pytest-httpx for SaaS proxy mocking
    - tmp_path fixture for isolated ~/.sco-compliance-os/

Test isolation strategy:
    - Ogni test usa un temp_data_dir via override Settings.data_dir
    - get_settings() cache cleared all'inizio di ogni test
    - get_license_client() singleton cleared all'inizio di ogni test
    - Store singleton resettato fra test per evitare DB sharing
"""
