package bootc

import "os/exec"

// BaseHasDnf starts the image without network and reports whether it ships
// dnf, the precondition of the rpm based legacy installer path (see InitDNF).
func BaseHasDnf(ref string) (bool, error) {
	cnt, err := NewContainer(ref)
	if err != nil {
		return false, err
	}
	/* #nosec G204 */
	found := exec.Command("podman", "exec", cnt.id, "sh", "-c", `command -v dnf`).Run() == nil
	if err := cnt.Stop(); err != nil {
		return false, err
	}
	return found, nil
}
