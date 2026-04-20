---
name: Bug Report
about: Report a bug to help us improve
title: '[BUG] '
labels: 'bug'
assignees: ''
---

## 🐛 Bug Description

A clear and concise description of what the bug is.

## 📋 Steps to Reproduce

1. Run command: `generate-mcp --file my-openapi.yaml`
2. Observe error: ...
3. See error

## ✅ Expected Behavior

What you expected to happen.

## ❌ Actual Behavior

What actually happened.

## 📄 OpenAPI Specification

Please provide a minimal OpenAPI spec that reproduces the issue (sanitize if needed):

```yaml
openapi: 3.0.0
info:
  title: Example API
  version: 1.0.0
paths:
  /example:
    get:
      # ...
```

Or link to a public spec that demonstrates the issue.

## 💻 Environment

- **OS**: [e.g., Windows 11, macOS 14, Ubuntu 22.04]
- **Python Version**: [e.g., 3.11.5]
- **MCP Generator Version**: [e.g., 3.1.1]
- **OpenAPI Generator Version**: [e.g., 7.10.0]
- **Installation Method**: [uv, pip, git clone]

## 📊 Error Output

```
Paste full error message and stack trace here
```

## 📸 Screenshots (if applicable)

Add screenshots to help explain the problem.

## 🔍 Additional Context

Add any other context about the problem here:
- Generated files that are incorrect
- Configuration settings you used
- Custom modifications to config files

## ✨ Possible Solution

If you have ideas on how to fix this, please share!

## 📝 Checklist

- [ ] I have searched existing issues to avoid duplicates
- [ ] I have provided a minimal reproducible example
- [ ] I have included all relevant error messages
- [ ] I have specified my environment details
