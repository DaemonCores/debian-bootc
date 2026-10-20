# Image boot test and rollback

This sequence describes how every built image is validated before publication. It starts after `podman build` when the image is installed onto a virtual disk and booted under QEMU/KVM with UEFI, and ends when the pre-reboot `tests` and post-rollback `reboot_tests` from `workflows/tests.yml` all pass, unblocking the push [src: file: workflows/tests.yml:1] [src: file: workflows/tests.yml:311]. Tests carry optional `arch`/`variant` gates (SKIP, not FAIL) and a mandatory `diag` [src: file: workflows/tests.yml:9] [src: file: workflows/tests.yml:13].

```mermaid
sequenceDiagram
    participant Runner as CI runner
    participant VM as QEMU VM
    participant Bootc as bootc on VM

    Runner->>Runner: bootc install image to virtual disk
    Runner->>VM: boot disk with UEFI firmware
    Runner->>VM: wait for SSH up to boot_timeout 900s
    loop each test in tests
        alt arch or variant mismatch
            Runner->>Runner: report SKIP
        else applicable
            Runner->>VM: run test command over SSH
            alt exit 0 or expect matched
                VM-->>Runner: PASS
            else failure
                Runner->>VM: run diag command
                VM-->>Runner: diagnostic output
            end
        end
    end
    Runner->>VM: touch /var/rollback-test-marker
    Runner->>Bootc: bootc rollback
    Bootc-->>Runner: rollbackQueued is true
    Runner->>VM: reboot and wait up to reboot_timeout 300s
    loop each test in reboot_tests
        Runner->>VM: verify marker kept and rollback consumed
    end
    Runner->>Runner: allow push only if nothing failed
```
