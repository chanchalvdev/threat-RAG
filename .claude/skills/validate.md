# Skill: validate

Run the full ThreatRAG validation suite.

## Steps
1. Lint backend: `cd threatrag/backend && ruff check app/`
2. Type-check backend: `mypy app/ --ignore-missing-imports`
3. Unit tests: `pytest tests/unit -v`
4. Health check: `curl -s http://localhost:8000/health | jq .`
5. Readiness check: `curl -s http://localhost:8000/health/ready | jq .`
6. Frontend type-check: `cd threatrag/web && npm run typecheck`
7. Frontend tests: `npm run test -- --run`

## Pass Criteria
- All linting and type checks exit 0
- All unit tests pass
- Health endpoints return expected JSON
- No TypeScript errors
