# Security and Public Sharing

## Demo boundary

This is an educational sample using fictional recall and inventory data. Do not use it to make clinical decisions or manage real pharmaceutical recalls.

The local Control Tower has no caller authentication. A typed approver name is a demonstration label, not a verified identity. Keep it bound to `127.0.0.1`; do not publish it through a tunnel or run it as an Internet-facing service.

Approvals, inventory changes, replay protection, and audit entries are held in memory. They are not durable, tamper-evident, or coordinated across replicas. The hosted workflow only reads data and summarizes it; it cannot approve or quarantine stock, and is not connected to the browser's live state.

Before production use, add verified identity, authorization bound to each approval, durable transactional state, expiry and replay controls, input limits, monitoring, and independent security review.

## Before publishing

1. Keep credentials and environment-specific deployment state outside source control. Use the committed environment template with your own local values.
2. Run `python scripts/check_repository.py` from the repository root.
3. Select and review the files to stage, then run `python scripts/check_repository.py --staged` to inspect their actual index contents.
4. Review screenshots, speaker notes, document metadata, and Git history separately. The checker is a limited pattern scan, not a secret-free guarantee.
5. Enable repository secret scanning, push protection, and dependency alerts where available. Restrict any deployment workflow to a protected environment with explicit reviewers.

If a credential was committed, revoke or rotate it first. Deleting the file or adding an ignore rule does not remove it from history.

## Reporting a vulnerability

Use the repository's **Security > Report a vulnerability** option when private reporting is enabled. Otherwise contact the repository owner privately through their published contact channel. Do not include tokens, personal data, or exploitable deployment details in a public issue.