# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| v1.x.x  | ✅ Yes    |

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Email: shashankdev@dmechatronix.in  
Subject: `[NEXUS SECURITY] Brief description`

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You'll receive a response within 48 hours. If confirmed, a patch will be released within 7 days and you'll be credited in the changelog.

## Scope

- Code execution sandbox bypass in `run_python` tool
- Path traversal in file I/O tools
- Memory injection attacks via ChromaDB
- Any issue that could affect users running NEXUS locally
