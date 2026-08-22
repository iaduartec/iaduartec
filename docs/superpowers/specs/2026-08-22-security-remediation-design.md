# Security Findings Remediation Design

**Goal:** Close the validated security findings from scan `94954225-f8ac-4093-b07c-94909f2f8620`, remove only proven stale content, and make the GitHub-facing repositories safe and documented.

**Scope:** `/home/ubuntu/portfolio-repo`, `/home/ubuntu/mission-bridge`, `/home/ubuntu/duartec-infra`, `/home/ubuntu/apps/insforge`, and `/home/ubuntu/projects/trading`. Source changes stay in isolated branches/worktrees; no service restart, deploy, push, or PR creation is implied.

**Security invariants:** Browser code must never carry a credential accepted for privileged server or n8n operations; shell and URL inputs must be validated at the shared boundary; secrets must come from runtime secret injection; database rows must be isolated by authenticated owner/tenant; resource and network boundaries must be bounded; tracked GitHub content must exclude secrets, private data, generated output, and stale artifacts.

**Compatibility:** Preserve legitimate local portfolio fallback behavior, approved YouTube transcript retrieval, existing internal service routes, and documented development commands. If a complete fix requires a missing product decision (for example, a real user-authentication provider), record the finding as blocked rather than weakening the boundary.

**Verification:** Each change gets a focused malicious-input regression and a legitimate control, then the repository-native check. Infrastructure changes get syntax/config validation without restarting production services. A final tracked-file and secret scan is required before any publication decision.
