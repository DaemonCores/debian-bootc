package install

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// The registry pull verifies the image against the sigstore policy and keeps
// the signature in containers-storage. skopeo then refuses to copy an image
// that carries signatures into an OCI layout ("Pushing signatures for OCI
// images is not supported"), which aborted every install from a signed image.
// The export must drop the signatures: they were already verified at pull time
// and the OCI directory is a private scratch copy for bootc.
func TestOCIExportDropsSignatures(t *testing.T) {
	dir, err := os.MkdirTemp(".", ".skopeo-sig-")
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
	for _, name := range []string{"skopeo", "mount", "umount"} {
		if err = os.WriteFile(filepath.Join(bin, name), []byte(fake), 0o700); err != nil {
			t.Fatal(err)
		}
	}
	t.Setenv("PATH", bin+":"+os.Getenv("PATH"))
	t.Setenv("CAPTURE", log)
	if err = skopeoExportOCI("ghcr.io/example/image:tag", filepath.Join(dir, "oci"), filepath.Join(dir, "tmp")); err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(log)
	if err != nil {
		t.Fatal(err)
	}
	for _, call := range strings.Split(strings.TrimSpace(string(raw)), "\n") {
		if strings.HasPrefix(call, "skopeo copy ") {
			if !strings.Contains(call, " --remove-signatures ") {
				t.Fatalf("skopeo copy keeps signatures, OCI layouts cannot store them: %s", call)
			}
			return
		}
	}
	t.Fatalf("no skopeo copy call recorded:\n%s", raw)
}
