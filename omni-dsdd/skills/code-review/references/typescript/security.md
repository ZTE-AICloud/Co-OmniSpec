---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Security

> This file extends [common/security.md](../common/security.md) with TypeScript/JavaScript specific content.

## Secret Management

```typescript
// NEVER: Hardcoded secrets
const apiKey = "sk-proj-xxxxx"

// ALWAYS: Environment variables
const clientToken = process.env.EXAMPLE_PROVIDER_KEY

if (!clientToken) {
  throw new Error('EXAMPLE_PROVIDER_KEY not configured')
}
```

## Agent Support

- Use **security-review** skill for comprehensive security audits
