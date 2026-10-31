package post

import (
	"bytes"
	"fmt"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/tuna-os/fisherman/internal/runner"
)

// localeRe matches a glibc locale name with an explicit charset, such as
// "fr_FR.UTF-8" or "sr_RS.UTF-8@latin". Anything else is refused so the value
// can never inject a line into the files it is written to.
var localeRe = regexp.MustCompile(`^[A-Za-z]{1,3}(_[A-Za-z0-9]+)?\.[A-Za-z0-9-]+(@[A-Za-z0-9]+)?$`)

// xkbTokenRe matches the values of the XKB settings: comma separated names of
// letters, digits and underscores (layouts and variants), possibly empty.
var xkbTokenRe = regexp.MustCompile(`^[A-Za-z0-9_]+(,[A-Za-z0-9_]+)*$`)

// WriteLocale selects the system language of the installed system at target:
// it writes the chosen locale to /etc/default/locale (LANG) and to
// /etc/locale.gen, the two files the Debian locales package reads. Generating
// the locale data is not done here.
func WriteLocale(target, locale string) error {
	if !localeRe.MatchString(locale) {
		return fmt.Errorf("invalid locale %q", locale)
	}
	etcDir, err := deployEtcDir(target)
	if err != nil {
		return err
	}
	if err := runner.Run("mkdir", "-p", filepath.Join(etcDir, "default")); err != nil {
		return fmt.Errorf("mkdir %s: %w", etcDir, err)
	}
	// The charset is the part after the dot, without the modifier.
	charset := strings.SplitN(strings.SplitN(locale, ".", 2)[1], "@", 2)[0]
	files := []struct{ path, content string }{
		{filepath.Join(etcDir, "default", "locale"), "LANG=" + locale + "\n"},
		{filepath.Join(etcDir, "locale.gen"), locale + " " + charset + "\n"},
	}
	for _, f := range files {
		if err := runner.RunWithStdin(bytes.NewBufferString(f.content), "tee", f.path); err != nil {
			return fmt.Errorf("writing %s: %w", f.path, err)
		}
	}
	return nil
}

// WriteKeyboard writes the keyboard layout of the installed system at target
// to /etc/default/keyboard, the file keyboard-configuration and console-setup
// read for the console and for the graphical session. The model, the layout
// and the variant must be XKB names; the variant may be empty.
func WriteKeyboard(target, model, layout, variant string) error {
	if !xkbTokenRe.MatchString(model) || !xkbTokenRe.MatchString(layout) ||
		(variant != "" && !xkbTokenRe.MatchString(variant)) {
		return fmt.Errorf("invalid keyboard %q/%q/%q", model, layout, variant)
	}
	etcDir, err := deployEtcDir(target)
	if err != nil {
		return err
	}
	dir := filepath.Join(etcDir, "default")
	if err := runner.Run("mkdir", "-p", dir); err != nil {
		return fmt.Errorf("mkdir %s: %w", dir, err)
	}
	content := fmt.Sprintf("XKBMODEL=%q\nXKBLAYOUT=%q\nXKBVARIANT=%q\nXKBOPTIONS=\"\"\nBACKSPACE=\"guess\"\n",
		model, layout, variant)
	path := filepath.Join(dir, "keyboard")
	if err := runner.RunWithStdin(bytes.NewBufferString(content), "tee", path); err != nil {
		return fmt.Errorf("writing %s: %w", path, err)
	}
	return nil
}
