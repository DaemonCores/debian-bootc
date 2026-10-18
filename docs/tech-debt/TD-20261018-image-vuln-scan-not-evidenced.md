---
name: td-20261018-image-vuln-scan-not-evidenced
description: No container vulnerability scan (trivy/grype/snyk) is visible for the published bootc images; the build lives in an external shared workflow.
metadata:
  type: tech-debt
  audit_history:
    - date: 2026-10-18
      status: Inferred
      reviewer: Docker audit 0.8.2
      note: first detection; image build job is outside this repo
    - date: 2026-10-18
      status: Confirmed by user
      reviewer: Kronn audit validation card
      note: "Confirmed through an audit validation card."
---

# TD-20261018-image-vuln-scan-not-evidenced

- **Area**: CI
- **Category**: docker
- **Severity**: Medium
- **Status**: Confirmed by user
- **Effort**: M
- **Blast radius**: module (5-10 files)

## Problem (fact)
`.github/workflows/pipeline.yml` only calls `DaemonCores/DaemonCores-CI/.github/workflows/full-pipeline.yml@main`; the image build, tag and push steps are defined there. No file in this repo references `trivy`, `grype`, `snyk` or an SBOM tool (grep over `.github/`, `workflows/`, `config.yml`). Whether the shared workflow scans images is not checkable from this repo. <!-- TODO: verify — DaemonCores-CI full-pipeline.yml is outside this repository -->

## Impact
Published OS images (kernel, firmware, openssh-server, podman, ~50 Debian packages) may ship known CVEs with no gate or report before cosign signing and push.

## Where (pointers)
- `.github/workflows/pipeline.yml:71` — delegation to the shared pipeline
- `.github/workflows/pipeline.yml:24-25` — monthly scheduled rebuild (only freshness mechanism visible)
- `workflows/tests.yml` — QEMU boot tests, no vulnerability scan

## Suggested direction
Confirm in DaemonCores-CI; if absent, add a `trivy image` / `grype` step after the image build (report-only at first, then fail on Critical).

## Next step
`create ticket`
