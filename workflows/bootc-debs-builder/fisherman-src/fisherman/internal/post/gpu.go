package post

import (
	"bytes"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/tuna-os/fisherman/internal/runner"
)

// SigEnforceArg is the kernel argument that makes the kernel refuse unsigned
// modules. The shipped kernel does not force it (MODULE_SIG_FORCE=n); the
// installer adds it, so the choice is made at install and not at build time.
const SigEnforceArg = "module.sig_enforce=1"

// gpuUsages are the GPU usage profiles dc-gpu understands.
var gpuUsages = map[string]bool{"gaming": true, "ia": true, "auto": true}

// gpuSets are the GPU module sets the image can deliver at install
// (GPU FINAL, owner 2026-11-03): the two open profile builds and their
// NVIDIA variants (loader policy + the linux-modules-nvidia base).
var gpuSets = map[string]bool{
	"gpu-ia":            true,
	"gpu-gaming":        true,
	"gpu-ia-nvidia":     true,
	"gpu-gaming-nvidia": true,
}

// WriteGPUProfile writes the GPU usage profile into /etc/dc-gpu/usage of the
// installed system at target, and /etc/dc-gpu/nvidia-consent when the NVIDIA
// EULA was accepted at install. These are the files dc-gpu reads.
func WriteGPUProfile(target, usage string, nvidiaConsent bool) error {
	if !gpuUsages[usage] {
		return fmt.Errorf("unknown GPU usage %q", usage)
	}
	etcDir, err := deployEtcDir(target)
	if err != nil {
		return err
	}
	dir := filepath.Join(etcDir, "dc-gpu")
	if err := runner.Run("mkdir", "-p", dir); err != nil {
		return fmt.Errorf("mkdir %s: %w", dir, err)
	}
	path := filepath.Join(dir, "usage")
	if err := runner.RunWithStdin(bytes.NewBufferString(usage+"\n"), "tee", path); err != nil {
		return fmt.Errorf("writing %s: %w", path, err)
	}
	if !nvidiaConsent {
		return nil
	}
	path = filepath.Join(dir, "nvidia-consent")
	if err := runner.RunWithStdin(bytes.NewBufferString("accepted-at-install\n"), "tee", path); err != nil {
		return fmt.Errorf("writing %s: %w", path, err)
	}
	return nil
}

// GPUModprobePayloads is the live-image directory the shipped loader policy
// confs of the GPU module sets live in (verbatim copies of the files the set
// debs carry — a fisherman unit test pins the delivered name).
const GPUModprobePayloads = "/usr/share/debian-bootc/gpu-sets"

// WriteGPUModuleSet records the GPU module set the install chose in
// /etc/dc-gpu/set of the installed system at target and copies its loader
// policy conf into /etc/modprobe.d/. The set deb itself is pulled at the
// first image update (or immediately when the gpu-set-stage helper of the
// live image can reach the APT repo); the set file tells update tooling and
// `dc-gpu` which build the machine runs. Fatal on failure so an install
// never silently drops the requested set.
func WriteGPUModuleSet(target, set string) error {
	if !gpuSets[set] {
		return fmt.Errorf("unknown GPU module set %q", set)
	}
	etcDir, err := deployEtcDir(target)
	if err != nil {
		return err
	}
	dir := filepath.Join(etcDir, "dc-gpu")
	if err := runner.Run("mkdir", "-p", dir); err != nil {
		return fmt.Errorf("mkdir %s: %w", dir, err)
	}
	path := filepath.Join(dir, "set")
	if err := runner.RunWithStdin(bytes.NewBufferString(set+"\n"), "tee", path); err != nil {
		return fmt.Errorf("writing %s: %w", path, err)
	}
	// Loader policy: /etc/modprobe.d/dc-gpu-<usage>*.conf of the set.
	conf := "dc-gpu-" + strings.TrimPrefix(set, "gpu-") + ".conf"
	confDir := filepath.Join(etcDir, "modprobe.d")
	if err := runner.Run("mkdir", "-p", confDir); err != nil {
		return fmt.Errorf("mkdir %s: %w", confDir, err)
	}
	payload := filepath.Join(GPUModprobePayloads, conf)
	if err := runner.Run("cp", payload, filepath.Join(confDir, conf)); err != nil {
		return fmt.Errorf("copying loader policy %s: %w", payload, err)
	}
	return nil
}

// EnsureKernelArg adds arg to the options line of every BLS loader entry of
// the installed system under sysroot (GRUB layout and systemd-boot layout),
// without duplicating it. Unlike the Plymouth arguments it is not optional:
// it returns an error when no entry exists, so the caller can refuse to
// finish an install that silently dropped the requested argument.
//
// Returns the number of entries modified.
func EnsureKernelArg(sysroot, arg string) (int, error) {
	total := 0
	found := false
	for _, dir := range []string{
		filepath.Join(sysroot, "boot", "loader", "entries"),
		filepath.Join(sysroot, "boot", "efi", "loader", "entries"),
	} {
		entries, err := filepath.Glob(filepath.Join(dir, "*.conf"))
		if err != nil || len(entries) == 0 {
			continue
		}
		found = true
		for _, entry := range entries {
			changed, err := ensureArgInEntry(entry, arg)
			if err != nil {
				return total, fmt.Errorf("patching %s: %w", entry, err)
			}
			if changed {
				total++
			}
		}
	}
	if !found {
		return 0, fmt.Errorf("no BLS loader entries found under %s", filepath.Join(sysroot, "boot"))
	}
	return total, nil
}
