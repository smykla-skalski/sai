# Authoritative References & Key Principles

## Contents
- Authoritative References
- Key Principles

---

## Authoritative References

When citing deductions, use these sources:

- **Official Best Practices**: https://code.claude.com/docs/en/best-practices
- **Official Memory Docs**: https://code.claude.com/docs/en/memory
- **Anthropic Blog**: https://claude.com/blog/using-claude-md-files
- **Anthropic Internal PDF**: https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf
- **Builder.io**: https://www.builder.io/blog/claude-md-guide
- **HumanLayer**: https://www.humanlayer.dev/blog/writing-a-good-claude-md
- **Arize**: https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/
- **Maxitect**: https://www.maxitect.blog/posts/maximising-claude-code-building-an-effective-claudemd
- **Dometrain**: https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/

---

## Key Principles

These principles guide both scoring and fixing:

- **Brevity is #1**: "Bloated CLAUDE.md files cause Claude to ignore your actual instructions" (Official)
- **~150 instruction limit**: "Frontier LLMs can follow approximately 150-200 instructions consistently. Claude Code's system prompt already contains ~50." (HumanLayer)
- **Commands are highest-value**: Exact build/test/lint commands Claude cannot guess (Builder.io)
- **Pointers over copies**: Use `file:line` references, not embedded code snippets (HumanLayer)
- **Alternatives, not negatives**: "Use Y instead of X" not "Never use X" (Arize)
- **No README duplication**: CLAUDE.md is for AI-operational context, not human onboarding (Official)
- **Modularize with rules/**: Use `.claude/rules/` for detailed topic files, keep root CLAUDE.md lean (Official)
- **Use hooks for deterministic actions**: "Unlike CLAUDE.md instructions which are advisory, hooks are deterministic" (Official)
- **The "First 5 Minutes" Test**: Could a new dev build, test, and contribute reading only this file? (Community)
- **Treat it like code**: Review when things go wrong, prune regularly (Official)
