package post_test

import (
	"path/filepath"
	"strings"
	"testing"

	"github.com/tuna-os/fisherman/internal/post"
)

func TestWriteLocale(t *testing.T) {
	target, deploy := ostreeTarget(t)
	calls := recordRuns(t)
	if err := post.WriteLocale(target, "fr_FR.UTF-8"); err != nil {
		t.Fatal(err)
	}
	etc := filepath.Join(deploy, "etc")
	want := []struct{ argv, stdin string }{
		{"mkdir -p " + filepath.Join(etc, "default"), ""},
		{"tee " + filepath.Join(etc, "default", "locale"), "LANG=fr_FR.UTF-8\n"},
		{"tee " + filepath.Join(etc, "locale.gen"), "fr_FR.UTF-8 UTF-8\n"},
	}
	if len(*calls) != len(want) {
		t.Fatalf("calls = %v", *calls)
	}
	for i, w := range want {
		if got := strings.Join((*calls)[i].argv, " "); got != w.argv || (*calls)[i].stdin != w.stdin {
			t.Errorf("call %d = %q / %q, want %q / %q", i, got, (*calls)[i].stdin, w.argv, w.stdin)
		}
	}
}

func TestWriteLocale_Modifier(t *testing.T) {
	target, _ := ostreeTarget(t)
	calls := recordRuns(t)
	if err := post.WriteLocale(target, "sr_RS.UTF-8@latin"); err != nil {
		t.Fatal(err)
	}
	if got := (*calls)[2].stdin; got != "sr_RS.UTF-8@latin UTF-8\n" {
		t.Errorf("locale.gen = %q", got)
	}
}

func TestWriteLocale_RejectsInjection(t *testing.T) {
	target, _ := ostreeTarget(t)
	calls := recordRuns(t)
	for _, bad := range []string{"", "fr_FR", "fr_FR.UTF-8\nLANG=C", "fr FR.UTF-8", "../x.UTF-8"} {
		if err := post.WriteLocale(target, bad); err == nil {
			t.Errorf("%q accepted", bad)
		}
	}
	if len(*calls) != 0 {
		t.Fatalf("invalid locale wrote %v", *calls)
	}
}

func TestWriteKeyboard(t *testing.T) {
	target, deploy := ostreeTarget(t)
	calls := recordRuns(t)
	if err := post.WriteKeyboard(target, "pc105", "fr", "oss"); err != nil {
		t.Fatal(err)
	}
	file := filepath.Join(deploy, "etc", "default", "keyboard")
	if len(*calls) != 2 || strings.Join((*calls)[1].argv, " ") != "tee "+file {
		t.Fatalf("calls = %v", *calls)
	}
	want := "XKBMODEL=\"pc105\"\nXKBLAYOUT=\"fr\"\nXKBVARIANT=\"oss\"\nXKBOPTIONS=\"\"\nBACKSPACE=\"guess\"\n"
	if (*calls)[1].stdin != want {
		t.Errorf("content = %q", (*calls)[1].stdin)
	}
}

func TestWriteKeyboard_EmptyVariantAndRejects(t *testing.T) {
	target, _ := ostreeTarget(t)
	calls := recordRuns(t)
	if err := post.WriteKeyboard(target, "pc105", "us", ""); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains((*calls)[1].stdin, "XKBVARIANT=\"\"\n") {
		t.Errorf("content = %q", (*calls)[1].stdin)
	}
	n := len(*calls)
	for _, bad := range [][3]string{
		{"", "us", ""}, {"pc105", "", ""}, {"pc105", "us\nX=1", ""}, {"pc105", "us", "a b"}, {"pc105", "u\"s", ""},
	} {
		if err := post.WriteKeyboard(target, bad[0], bad[1], bad[2]); err == nil {
			t.Errorf("%q accepted", bad)
		}
	}
	if len(*calls) != n {
		t.Fatalf("invalid keyboard wrote %v", (*calls)[n:])
	}
}
