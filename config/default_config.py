from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "path": "./Downloaded/",
    "music": True,
    "cover": True,
    "avatar": True,
    "json": True,
    "start_time": "",
    "end_time": "",
    "folderstyle": True,
    "mode": ["post"],
    "number": {
        "post": 0,
        "like": 0,
        "allmix": 0,
        "mix": 0,
        "music": 0,
        "collect": 0,
        "collectmix": 0,
    },
    "increase": {
        "post": False,
        "like": False,
        "allmix": False,
        "mix": False,
        "music": False,
    },
    "thread": 5,
    "retry_times": 3,
    "rate_limit": 2,
    "proxy": "",
    "database": True,
    "database_path": "dy_downloader.db",
    "progress": {
        "quiet_logs": True,
    },
    "transcript": {
        "enabled": False,
        "provider": "openai_api",  # "openai_api", "local", "auto"
        "model": "gpt-4o-mini-transcribe",
        "local_model": "small",  # for local whisper: tiny/base/small/medium/large
        "language_hint": "zh",
        "output_dir": "",
        "response_formats": ["txt", "json"],
        "api_url": "https://api.openai.com/v1/audio/transcriptions",
        "api_key_env": "OPENAI_API_KEY",
        "api_key": "",
    },
    "archive": {
        "enabled": True,  # generate markdown archive when transcript is enabled
        "output_dir": "",  # empty = same dir as transcript
        "raw": False,  # skip paragraph formatting
    },
    "analysis": {
        "enabled": True,  # generate analysis JSON when transcript is enabled
        "output_dir": "",  # empty = same dir as transcript
    },
    "auto_cookie": False,
    "browser_fallback": {
        "enabled": True,
        "headless": False,
        "max_scrolls": 240,
        "idle_rounds": 8,
        "wait_timeout_seconds": 600,
    },
}
