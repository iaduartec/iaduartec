Audit every relevant repository and Codex configuration under /home/ubuntu.

Do not modify project files during discovery.

Use subagents aggressively when independent repository inspection can run
in parallel and doing so improves speed.

Delegate discovery primarily to explorer agents.

Inventory:

- Git repositories
- active branches
- uncommitted work
- AGENTS.md
- .codex directories
- skills
- agents
- hooks
- MCP
- CI/CD
- Docker
- systemd integration
- OpenAI API usage
- Codex configuration
- model references
- deprecated OpenAI API usage
- duplicated instructions
- contradictory instructions

Exclude heavyweight generated directories such as:

.git/objects
node_modules
.next
dist
build
coverage
cache directories
large logs
Docker volumes

Classify repositories:

A = critical / active
B = active / secondary
C = experimental
D = legacy

Create:

/home/ubuntu/ASTRA_MIGRATION_AUDIT.md

with:

REPO
STACK
STATUS
CURRENT MODEL
AGENTS
SKILLS
CI
OPENAI USAGE
TECHNICAL DEBT
MIGRATION RISK
RECOMMENDED ACTION

Then synthesize findings as root orchestrator.

Do not migrate anything yet.
