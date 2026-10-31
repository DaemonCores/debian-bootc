package post_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/tuna-os/fisherman/internal/post"
)

func TestWriteGPUProfile_RejectsUnknownUsage(t *testing.T) {
	calls := recordRuns(t)
	if err := post.WriteGPUProfile(t.TempDir(), "evil", false); err == nil {
		t.Fatal("unknown usage accepted")
	}
	if len(*calls) != 0 {
		t.Fatalf("invalid usage ran %v", *calls)
	}
}

func TestWriteGPUProfile(t *testing.T) {
	for _, tc := range []struct {
		consent bool
		writes  int
	}{{false, 1}, {true, 2}} {
		target, deploy := ostreeTarget(t)
		calls := recordRuns(t)
		if err := post.WriteGPUProfile(target, "ia", tc.consent); err != nil {
			t.Fatal(err)
		}
		dir := filepath.Join(deploy, "etc", "dc-gpu")
		if len(*calls) != 1+tc.writes ||
			strings.Join((*calls)[0].argv, " ") != "mkdir -p "+dir ||
			strings.Join((*calls)[1].argv, " ") != "tee "+filepath.Join(dir, "usage") ||
			(*calls)[1].stdin != "ia\n" {
			t.Errorf("consent=%v calls = %v", tc.consent, *calls)
		}
		if tc.consent &&
			strings.Join((*calls)[2].argv, " ") != "tee "+filepath.Join(dir, "nvidia-consent") {
			t.Errorf("consent file not written: %v", *calls)
		}
	}
}

func writeEntry(t *testing.T, sysroot, options string) string {
	t.Helper()
	dir := filepath.Join(sysroot, "boot", "loader", "entries")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "ostree-1.conf")
	if err := os.WriteFile(path, []byte("title x\noptions "+options+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestEnsureKernelArg_AddsOnceToEveryEntry(t *testing.T) {
	sysroot := t.TempDir()
	path := writeEntry(t, sysroot, "root=UUID=abc rw")
	for i, want := range []int{1, 0} {
		n, err := post.EnsureKernelArg(sysroot, post.SigEnforceArg)
		if err != nil || n != want {
			t.Fatalf("run %d: n=%d err=%v, want n=%d", i, n, err, want)
		}
	}
	data, _ := os.ReadFile(path)
	if got := strings.Count(string(data), "module.sig_enforce=1"); got != 1 {
		t.Errorf("argument present %d times in %q", got, data)
	}
}

func TestEnsureKernelArg_NoEntryIsAnError(t *testing.T) {
	if _, err := post.EnsureKernelArg(t.TempDir(), post.SigEnforceArg); err == nil {
		t.Fatal("missing loader entries went unnoticed")
	}
}
