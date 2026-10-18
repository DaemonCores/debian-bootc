# ISO installation

This sequence describes how the amd64 installer ISO deploys debian-bootc onto a disk. The ISO is built from `Containerfile.iso` on top of `ghcr.io/daemoncores/debian-bootc:latest-${ARCH}-autoupdate` and converted by bootc-image-builder, with the clean base image as the install payload [src: file: Containerfile.iso:16] [src: file: Containerfile.iso:28]. It starts at live boot (autologin on tty1 into cage and the bootc-installer wizard) and ends when fisherman has run `bootc install to-filesystem` on the target disk [src: file: Containerfile.iso:12] [src: file: docs/architecture.md:90].

```mermaid
sequenceDiagram
    actor Operator
    participant Getty as tty1 autologin
    participant Cage as cage compositor
    participant Wizard as bootc-installer
    participant Polkit as polkit pkexec
    participant Fish as fisherman
    participant Disk as Target disk
    participant Reg as GHCR

    Operator->>Getty: boot live ISO
    Getty->>Cage: autologin user live
    Cage->>Wizard: launch GTK4 wizard
    Wizard->>Wizard: load images from recipe.json
    Operator->>Wizard: pick image, disk and Btrfs or XFS
    Wizard->>Polkit: pkexec fisherman
    Polkit-->>Wizard: allowed without password for live
    Wizard->>Fish: start install
    Fish->>Disk: create partitions and filesystem
    alt online ISO
        Fish->>Reg: pull registry image
    else offline ISO
        Fish->>Fish: use embedded OCI archive
    end
    Fish->>Disk: bootc install to-filesystem
    Note over Fish,Disk: registry ref kept as upgrade source
    Fish-->>Wizard: install complete
```
