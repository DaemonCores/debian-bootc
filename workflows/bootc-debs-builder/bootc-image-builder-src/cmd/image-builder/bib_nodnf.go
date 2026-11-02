package main

import (
	"slices"

	"github.com/osbuild/image-builder/pkg/olog"
	"github.com/osbuild/image-builder/pkg/bootc"
)

// isoTypeForBase maps the legacy rpm based "iso" and "anaconda-iso" image
// types to the container based "bootc-installer" when the base image cannot
// run the rpm installer path: no dnf in the base image and no separate build
// container was given. The rpm path needs dnf in the build container to
// depsolve anaconda and lorax; a base without dnf has nothing to resolve, while
// the container based installer needs no package manager.
func isoTypeForBase(imgref, buildImgref string, imgTypes []string) []string {
	if buildImgref != "" {
		return imgTypes
	}
	if !slices.Contains(imgTypes, "iso") && !slices.Contains(imgTypes, "anaconda-iso") {
		return imgTypes
	}
	hasDnf, err := bootc.BaseHasDnf(imgref)
	if err != nil || hasDnf {
		return imgTypes
	}
	olog.Printf("no dnf in %s: building the iso with the container based bootc-installer type", imgref)
	mapped := make([]string, len(imgTypes))
	for i, t := range imgTypes {
		if t == "iso" || t == "anaconda-iso" {
			t = "bootc-installer"
		}
		mapped[i] = t
	}
	return mapped
}
