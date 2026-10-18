# CI build and publish pipeline

This sequence describes how a change becomes published packages and images. It starts when a push to `main` (or a monthly cron / manual dispatch) triggers `.github/workflows/pipeline.yml`, which delegates to the shared `DaemonCores-CI/full-pipeline.yml@main` [src: file: .github/workflows/pipeline.yml:17] [src: file: .github/workflows/pipeline.yml:71]. It ends with signed `.deb`s on GitHub Pages and cosign-signed images on GHCR [src: file: docs/architecture.md:39] [src: file: docs/architecture.md:102].

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub Actions
    participant Plan as Plan job
    participant EnvJob as Env job
    participant Debs as Debs builder
    participant Pages as GitHub Pages APT repo
    participant Img as Image job
    participant Harness as QEMU test harness
    participant Reg as GHCR

    Dev->>GH: push to main
    GH->>Plan: run full-pipeline.yml
    Plan->>Plan: diff push and select stages
    opt rebuild_env or monthly
        Plan->>EnvJob: build buildenv from env.yml
        EnvJob->>Reg: push repo-buildenv image
    end
    Plan->>Debs: read packages.yml and compute waves
    loop each wave
        Debs->>Debs: hash sources and env per package
        alt hash unchanged
            Debs->>Pages: restore cached deb
        else hash changed
            Debs->>Debs: run build script in buildenv
        end
    end
    Debs->>Pages: publish signed APT index
    Plan->>Img: matrix of Containerfile x arch x update mode
    Img->>Pages: apt install custom stack
    Img->>Img: podman build and bootc validation
    Img->>Harness: install image to virtual disk
    Harness->>Harness: boot QEMU and run tests.yml over SSH
    alt all tests pass
        Harness->>Reg: push image and sign with cosign
        Reg->>Reg: publish multi-arch manifest lists
    else a test fails
        Harness-->>GH: run diag and fail the job
    end
```
