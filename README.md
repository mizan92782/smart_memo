# Smart Memo System — Agent Skills Kit

This starter kit gives repository-aware coding agents durable, feature-specific guidance for building Smart Memo System.

## Install
Copy `AGENTS.md` to the repository root and copy `.agents/skills/` into the project. If your agent uses another skills directory convention, adapt the path but keep the skill content.

## How the agent should use skills
- Start with `saas-architecture` and `security-tenant-isolation`.
- Read the feature skill matching the task.
- Read cross-cutting skills when relevant: `database-atomicity`, `query-optimization`, `pagination`, `caching`, `testing`, and `security`.
- Update a skill after discovering a reusable project convention or a confirmed business rule.
- Keep confirmed decisions separate from assumptions. Do not silently turn assumptions into requirements.

## Important business decisions to confirm
1. Can one vendor own multiple stores?
2. Can one customer memo contain products from multiple stores? Recommended default: no; one order/memo per store.
3. Is stock reserved on order submission or deducted only at fulfillment? Recommended: reserve on accepted order, deduct/convert reservation at fulfillment, release on eligible cancellation.
4. Can a vendor accept orders with insufficient stock or allow backorders?
5. Which units and conversions are allowed for each product?
6. Are partial fulfillment, substitutions, returns and refunds supported?
7. Which payment methods exist beyond cash on delivery?
8. Is delivery performed by store staff or a third-party service?
9. Are taxes, service charges, and delivery fees required?
10. Which database, backend framework, frontend framework, and deployment target are selected?

## Skill format
Each `SKILL.md` contains purpose, when to use it, rules, workflow, failure modes, and acceptance checks. Keep skills actionable and specific to this product.
