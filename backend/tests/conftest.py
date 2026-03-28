"""
conftest.py - MUST be loaded FIRST
Patches zep_cloud before any pytest collection
"""
import sys
import os

# ── Patch zep_cloud BEFORE any import chain ──────────────────────────────────
# pytest discovers test files, which import app.* packages,
# which import graph_builder.py, which imports zep_cloud.
# This must run FIRST so zep_cloud is already mocked when that import happens.
sys.modules['zep_cloud'] = type(sys)('zep_cloud')
sys.modules['zep_cloud.client'] = type(sys)('zep_cloud.client')
sys.modules['zep_cloud.client'].Zep = type('MockZep', (), {})

# ── Set up paths ────────────────────────────────────────────────────────────
_backend_dir = os.path.dirname(__file__)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Set up mock environment
os.environ.setdefault('LLM_API_KEY', 'test_key')
os.environ.setdefault('LLM_BASE_URL', 'https://api.groq.com/openai/v1')
os.environ.setdefault('LLM_MODEL_NAME', 'llama-3.3-70b-versatile')
os.environ.setdefault('MIROBET_AGENT_COUNT', '64')
os.environ.setdefault('FLASK_DEBUG', 'False')
