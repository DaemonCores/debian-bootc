package install

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// On a live ISO /var/tmp is a small RAM-backed overlay. containers/image
// stages layer blobs in /var/tmp whatever TMPDIR says, so the registry pull
// into the redirected store must run with /var/tmp bind-mounted over a
// disk-backed scratch directory, exactly like bootc install and the OCI
// export already do. Without it the pull dies with "no space left on device".
func TestRedirectedPullRunsWithDiskBackedVarTmp(t *testing.T) {
	dir, err := os.MkdirTemp(".", ".pull-vartmp-")
	if err != nil {
		t.Fatal(err)
	}
	dir, err = filepath.Abs(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(dir)
	log := filepath.Join(dir, "calls.log")
	fake := "#!/bin/sh\necho \"$(basename \"$0\") $*\" >> \"$CAPTURE\"\n"
	bin := filepath.Join(dir, "bin")
	if err = os.Mkdir(bin, 0o700); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"podman", "mount", "umount"} {
		if err = os.WriteFile(filepath.Join(bin, name), []byte(fake), 0o700); err != nil {
			t.Fatal(err)
		}
	}
	t.Setenv("PATH", bin+":"+os.Getenv("PATH"))
	t.Setenv("CAPTURE", log)
	oldSpace, oldDriver, oldExport := storageSpaceConstrainedFn, selectStorageDriverFn, SkopeoExportOCIFn
	defer func() {
		storageSpaceConstrainedFn = oldSpace
		selectStorageDriverFn = oldDriver
		SkopeoExportOCIFn = oldExport
	}()
	storageSpaceConstrainedFn = func() bool { return true }
	selectStorageDriverFn = func(string) (string, string) { return "overlay", "test" }
	SkopeoExportOCIFn = func(string, string, string) error { return nil }
	scratch := filepath.Join(dir, "scratch")
	err = BootcInstall(Options{
		SourceImgref: "ghcr.io/example/image:tag",
		NeedsPull:    true,
		Target:       filepath.Join(dir, "target"),
		ScratchDir:   scratch,
	})
	if err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(log)
	if err != nil {
		t.Fatal(err)
	}
	calls := strings.Split(strings.TrimSpace(string(raw)), "\n")
	bindCall := "mount --bind " + filepath.Join(scratch, "var-tmp-override") + " /var/tmp"
	bindAt, pullAt, unbindAt := -1, -1, -1
	for i, c := range calls {
		switch {
		case c == bindCall && bindAt < 0:
			bindAt = i
		case strings.HasPrefix(c, "podman ") && strings.HasSuffix(c, " pull ghcr.io/example/image:tag"):
			pullAt = i
		case c == "umount /var/tmp" && pullAt >= 0 && unbindAt < 0:
			unbindAt = i
		}
	}
	if pullAt < 0 {
		t.Fatalf("no podman pull recorded: %q", calls)
	}
	if bindAt < 0 || bindAt > pullAt {
		t.Fatalf("podman pull ran without /var/tmp bound to disk first: %q", calls)
	}
	if unbindAt < 0 {
		t.Fatalf("/var/tmp bind not released after the pull: %q", calls)
	}
}
