package post

import (
	"bytes"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/tuna-os/fisherman/internal/runner"
)

// sshRootPolicyFile is the sshd drop-in that carries the root login policy.
// The 01- prefix makes it win over later drop-ins, as the first-boot setup
// service it replaces did.
const sshRootPolicyFile = "01-permitrootlogin.conf"

// deployRoot returns the writable root of the deployment installed at target
// and whether the deployment is composefs-native (edited with --root) rather
// than ostree (edited through a chroot), as CreateUser does.
func deployRoot(target string) (string, bool, error) {
	if isComposeFsNative(target) {
		etcDir, err := ComposeFsDeployEtcDirFn(target)
		if err != nil {
			return "", false, fmt.Errorf("finding composefs deploy root: %w", err)
		}
		return filepath.Dir(etcDir), true, nil
	}
	deployDir, err := DeploymentDirFn(target)
	if err != nil {
		return "", false, fmt.Errorf("finding deployment dir: %w", err)
	}
	return deployDir, false, nil
}

// SetRootPassword sets the root password of the installed system at target.
// The password goes through chpasswd stdin so it never appears in ps output;
// a pre-hashed crypt(3) string ("$id$salt$hash") is written verbatim with -e.
// An empty password is a no-op.
func SetRootPassword(target, password string) error {
	if password == "" {
		return nil
	}
	root, composefs, err := deployRoot(target)
	if err != nil {
		return err
	}
	input := bytes.NewBufferString("root:" + password + "\n")
	flag := []string{}
	if strings.HasPrefix(password, "$") {
		flag = []string{"-e"}
	}
	if composefs {
		err = runner.RunWithStdin(input, "chpasswd", append([]string{"--root", root}, flag...)...)
	} else {
		err = runner.RunWithStdin(input, "chroot", append([]string{root, "chpasswd"}, flag...)...)
	}
	if err != nil {
		return fmt.Errorf("chpasswd root (%s): %w", root, err)
	}
	return nil
}

// WriteSSHRootPolicy writes the sshd root login policy ("yes" or "no") into
// the sshd drop-in directory of the installed system at target.
func WriteSSHRootPolicy(target string, allow bool) error {
	etcDir, err := deployEtcDir(target)
	if err != nil {
		return err
	}
	dir := filepath.Join(etcDir, "ssh", "sshd_config.d")
	if err := runner.Run("mkdir", "-p", dir); err != nil {
		return fmt.Errorf("mkdir %s: %w", dir, err)
	}
	value := "no"
	if allow {
		value = "yes"
	}
	path := filepath.Join(dir, sshRootPolicyFile)
	if err := runner.RunWithStdin(bytes.NewBufferString("PermitRootLogin "+value+"\n"), "tee", path); err != nil {
		return fmt.Errorf("writing %s: %w", path, err)
	}
	return nil
}
