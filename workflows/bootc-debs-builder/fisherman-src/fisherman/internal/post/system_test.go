package post_test

import (
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/tuna-os/fisherman/internal/post"
	"github.com/tuna-os/fisherman/internal/runner"
)

type call struct {
	stdin string
	argv  []string
}

// recordRuns replaces runner.RunFn with a recorder and restores it on cleanup.
func recordRuns(t *testing.T) *[]call {
	t.Helper()
	var calls []call
	old := runner.RunFn
	runner.RunFn = func(stdin io.Reader, name string, args ...string) error {
		if name == "ls" { // layout probe of isComposeFsNative: answer from the real tree
			_, err := os.Stat(args[0])
			return err
		}
		c := call{argv: append([]string{name}, args...)}
		if stdin != nil {
			b, _ := io.ReadAll(stdin)
			c.stdin = string(b)
		}
		calls = append(calls, c)
		return nil
	}
	t.Cleanup(func() { runner.RunFn = old })
	return &calls
}

func ostreeTarget(t *testing.T) (target, deploy string) {
	t.Helper()
	target = t.TempDir()
	deploy = filepath.Join(target, "ostree", "deploy", "default", "deploy", "abc123.0")
	if err := os.MkdirAll(deploy, 0o755); err != nil {
		t.Fatal(err)
	}
	post.DeploymentDirFn = func(string) (string, error) { return deploy, nil }
	t.Cleanup(func() { post.DeploymentDirFn = post.DefaultDeploymentDir })
	return target, deploy
}

func TestSetRootPassword_EmptyIsNoop(t *testing.T) {
	calls := recordRuns(t)
	if err := post.SetRootPassword(t.TempDir(), ""); err != nil {
		t.Fatal(err)
	}
	if len(*calls) != 0 {
		t.Fatalf("empty password ran %v", *calls)
	}
}

func TestSetRootPassword_OstreeChrootStdin(t *testing.T) {
	target, deploy := ostreeTarget(t)
	calls := recordRuns(t)
	if err := post.SetRootPassword(target, "s3cret-pass"); err != nil {
		t.Fatal(err)
	}
	if len(*calls) != 1 {
		t.Fatalf("calls = %v", *calls)
	}
	c := (*calls)[0]
	if got, want := strings.Join(c.argv, " "), "chroot "+deploy+" chpasswd"; got != want {
		t.Errorf("argv = %q, want %q", got, want)
	}
	if c.stdin != "root:s3cret-pass\n" {
		t.Errorf("stdin = %q", c.stdin)
	}
	if strings.Contains(strings.Join(c.argv, " "), "s3cret-pass") {
		t.Error("password leaked into argv")
	}
}

func TestSetRootPassword_HashedUsesE(t *testing.T) {
	target, deploy := ostreeTarget(t)
	calls := recordRuns(t)
	if err := post.SetRootPassword(target, "$6$salt$hash"); err != nil {
		t.Fatal(err)
	}
	if got, want := strings.Join((*calls)[0].argv, " "), "chroot "+deploy+" chpasswd -e"; got != want {
		t.Errorf("argv = %q, want %q", got, want)
	}
}

func TestWriteSSHRootPolicy(t *testing.T) {
	for _, tc := range []struct {
		allow bool
		want  string
	}{{true, "PermitRootLogin yes\n"}, {false, "PermitRootLogin no\n"}} {
		target, deploy := ostreeTarget(t)
		calls := recordRuns(t)
		if err := post.WriteSSHRootPolicy(target, tc.allow); err != nil {
			t.Fatal(err)
		}
		dir := filepath.Join(deploy, "etc", "ssh", "sshd_config.d")
		file := filepath.Join(dir, "01-permitrootlogin.conf")
		if len(*calls) != 2 ||
			strings.Join((*calls)[0].argv, " ") != "mkdir -p "+dir ||
			strings.Join((*calls)[1].argv, " ") != "tee "+file ||
			(*calls)[1].stdin != tc.want {
			t.Errorf("allow=%v calls = %v", tc.allow, *calls)
		}
	}
}
