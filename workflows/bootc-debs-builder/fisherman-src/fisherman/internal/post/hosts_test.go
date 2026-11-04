package post_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/tuna-os/fisherman/internal/post"
)

const bootstrapLine = "127.0.1.1	my-node.local my-node"

// writeHostsFile seeds the /etc/hosts of the test deployment.
func writeHostsFile(t *testing.T, deploy, content string) {
	t.Helper()
	path := filepath.Join(deploy, "etc", "hosts")
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readHostsFile(t *testing.T, deploy string) string {
	t.Helper()
	b, err := os.ReadFile(filepath.Join(deploy, "etc", "hosts"))
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}

func TestWriteHostsBootstrap_ReplacesPlaceholder(t *testing.T) {
	target, deploy := ostreeTarget(t)
	writeHostsFile(t, deploy,
		"127.0.0.1   localhost.localdomain localhost\n\n127.0.1.1   daemoncores-ve.local daemoncores-ve\n")
	if err := post.WriteHostsBootstrap(target, "my-node"); err != nil {
		t.Fatal(err)
	}
	want := "127.0.0.1   localhost.localdomain localhost\n\n" + bootstrapLine + "\n"
	if got := readHostsFile(t, deploy); got != want {
		t.Errorf("hosts = %q, want %q", got, want)
	}
}

func TestWriteHostsBootstrap_AppendsWhenMissing(t *testing.T) {
	target, deploy := ostreeTarget(t)
	writeHostsFile(t, deploy, "127.0.0.1   localhost.localdomain localhost\n")
	if err := post.WriteHostsBootstrap(target, "my-node"); err != nil {
		t.Fatal(err)
	}
	got := readHostsFile(t, deploy)
	if !strings.HasSuffix(got, bootstrapLine+"\n") {
		t.Errorf("bootstrap line missing: %q", got)
	}
}

func TestWriteHostsBootstrap_NoChangeIsNoop(t *testing.T) {
	target, deploy := ostreeTarget(t)
	want := "127.0.0.1   localhost.localdomain localhost\n\n" + bootstrapLine + "\n"
	writeHostsFile(t, deploy, want)
	if err := post.WriteHostsBootstrap(target, "my-node"); err != nil {
		t.Fatal(err)
	}
	if got := readHostsFile(t, deploy); got != want {
		t.Errorf("hosts changed to %q", got)
	}
}

func TestWriteHostsBootstrap_EmptyHostnameIsNoop(t *testing.T) {
	target, deploy := ostreeTarget(t)
	want := "127.0.1.1   old-name old-name\n"
	writeHostsFile(t, deploy, want)
	if err := post.WriteHostsBootstrap(target, ""); err != nil {
		t.Fatal(err)
	}
	if got := readHostsFile(t, deploy); got != want {
		t.Errorf("hosts changed to %q without a hostname", got)
	}
}