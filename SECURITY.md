# Security Policy for Temporal Flow Engine

## Secret Scanning

This repository uses multiple layers of secret protection:

### 1. Pre-commit Hooks
- Local git pre-commit hook scans for API keys, tokens, and other secrets
- Prevents commits containing secrets from entering git history
- Supports multiple secret types: OpenAI, AWS, GitHub, Google, Stripe, JWT tokens

### 2. GitHub Secret Scanning
- GitHub's built-in secret scanning is enabled (if available)
- Push protection prevents secrets from being pushed to remote
- Repository admins receive alerts for detected secrets

### 3. Environment Variables
All sensitive configuration should use environment variables:

```yaml
# ✅ CORRECT - Use environment variables
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}

# ❌ WRONG - Never hardcode secrets
environment:
  - OPENAI_API_KEY=sk-proj-actual-key-here
```

## Supported Secret Types

The pre-commit hook detects:
- OpenAI API keys (`sk-*`, `sk-proj-*`)
- AWS access keys and secrets
- GitHub tokens (`ghp_*`, `github_pat_*`)
- Google API keys (`AIza*`)
- Stripe keys (`pk_live_*`, `sk_live_*`)
- JWT tokens
- Other common secret patterns

## Emergency Procedures

If a secret is accidentally committed:

1. **Immediately revoke the exposed secret** at the provider
2. **Generate a new secret**
3. **Clean git history** using the repository's cleanup procedures
4. **Update environment variables** with the new secret

## Best Practices

1. Always use `.env` files for local development
2. Ensure `.env` is in `.gitignore`
3. Use environment variables in all configuration files
4. Never commit secrets, even temporarily
5. Use the `--no-verify` flag only in emergencies (not recommended)

## Bypassing Protection (Emergency Only)

```bash
# Only use in emergencies - NOT RECOMMENDED
git commit --no-verify -m "Emergency commit"
```

**Warning**: Bypassing secret protection can expose sensitive data!
