# GEE Porto Green Space Project

## Credentials

- GEE project ID lives in `.env` (gitignored), loaded via `python-dotenv`
- **Never hardcode** the project ID or any credential as a string literal in code
- Always use `os.environ["GEE_PROJECT"]` after calling `load_dotenv()`
- Asset paths use f-strings: `f'projects/{GEE_PROJECT}/assets/...'`
- If you spot hardcoded secrets in existing code, flag it immediately
