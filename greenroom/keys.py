"""Credential loader. Environment first, then a .env file at the repo root.

NEVER hard-code a token in this repo. The .env file is gitignored and stays local;
CI and any shared machine should export the variables instead.
"""
import os
import pathlib

ENV = pathlib.Path(__file__).resolve().parents[1] / ".env"


def _load(name):
    v = os.environ.get(name)
    if v:
        return v.strip()
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            line = line.strip()
            if line.startswith(name) and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        f"ERROR: {name} not set. Export it, or copy .env.example to .env and fill it in."
    )


def replicate_token():
    return _load("REPLICATE_API_TOKEN")


def openai_key():
    return _load("OPENAI_API_KEY")
