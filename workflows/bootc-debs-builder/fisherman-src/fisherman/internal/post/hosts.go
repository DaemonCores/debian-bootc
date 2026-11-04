package post

import (
	"bytes"
	"fmt"
	"os"
	"regexp"
	"path/filepath"

	"github.com/tuna-os/fisherman/internal/runner"
)

// hostsBootstrapRe matches the Debian 127.0.1.1 loopback bootstrap line of
// /etc/hosts: the entry that resolves the local hostname before any network
// is up (PVE-adjacent stacks — pmxcfs, pve-ssl — resolve the node name over
// loopback during multi-user boot). It is replaced with one that resolves the
// hostname the recipe chose.
var hostsBootstrapRe = regexp.MustCompile(`(?m)^127\.0\.1\.1[ \t]+\S.*`)

// HostnameRe mirrors the recipe CheckHostname validation: recipe hostname is
// pre-validated before the disk write, so the value interpolated into
// /etc/hosts is already constrained to letters, digits, hyphens and dots.
const HostnameRe = `^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$`

// WriteHostsBootstrap keeps the 127.0.1.1 bootstrap line of /etc/hosts in
// sync with the hostname the installer wrote (WriteHostname). The shipped
// image carries a placeholder bootstrap entry; a renamed host would leave it
// resolving the OLD name. The replacement line uses fqdn + shortname, the
// same shape the shipped postinstall entry has. Idempotent: an already
// matching /etc/hosts is left untouched.
func WriteHostsBootstrap(target, hostname string) error {
	if hostname == "" {
		return nil
	}
	if ok, _ := regexp.MatchString(HostnameRe, hostname); !ok {
		return fmt.Errorf("invalid hostname %q", hostname)
	}
	etcDir, err := deployEtcDir(target)
	if err != nil {
		return err
	}
	if err := runner.Run("mkdir", "-p", etcDir); err != nil {
		return fmt.Errorf("mkdir %s: %w", etcDir, err)
	}
	path := filepath.Join(etcDir, "hosts")
	hosts, err := os.ReadFile(path)
	if err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("reading %s: %w", path, err)
	}
	bootstrap := fmt.Sprintf("127.0.1.1\t%s.local %s", hostname, hostname)
	hostsFile := hostsBootstrapRe.ReplaceAllString(string(hosts), bootstrap)
	if !hostsBootstrapRe.MatchString(hostsFile) {
		if hostsFile != "" && !bytes.HasSuffix([]byte(hostsFile), []byte("\n")) {
			hostsFile += "\n"
		}
		hostsFile += bootstrap + "\n"
	}
	if hostsFile == string(hosts) {
		return nil
	}
	if err := runner.RunWithStdin(bytes.NewBufferString(hostsFile), "tee", path); err != nil {
		return fmt.Errorf("writing %s: %w", path, err)
	}
	return nil
}