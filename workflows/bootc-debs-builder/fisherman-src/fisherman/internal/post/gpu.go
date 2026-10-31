package post

import (
	"bytes"
	"fmt"
	"path/filepath"

	"github.com/tuna-os/fisherman/internal/runner"
)

// SigEnforceArg is the kernel argument that makes the kernel refuse unsigned
// modules. The shipped kernel does not force it (MODULE_SIG_FORCE=n); the
// installer adds it, so the choice is made at install and not at build time.
const SigEnforceArg = "module.sig_enforce=1"

// gpuUsages are the GPU usage profiles dc-gpu understands.
var gpuUsages = map[string]bool{"gaming": true, "ia": true, "auto": true}

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
