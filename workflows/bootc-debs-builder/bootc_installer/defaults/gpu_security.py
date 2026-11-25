"""GPU security step of the bootc installer.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from gettext import gettext as _
from typing import Protocol, cast

from gi.repository import (  # pyright: ignore[reportMissingModuleSource]
    Adw,
    Gtk,
)

from ..utils import gpu_config


class _FinalsProvider(Protocol):
    """A step that can return its merged finals."""

    def get_finals(self) -> dict[str, object]:
        """Return the merged finals of the step.

        Returns:
            The finals mapping of the step.

        Raises:
            NotImplementedError: Always; the protocol is never instantiated.
        """
        raise NotImplementedError


class _Window(Protocol):
    """The upstream installer window this step drives."""

    def next(self) -> None:
        """Advance to the next installer step."""


@Gtk.Template(
    resource_path="/org/bootcinstaller/Installer/gtk/default-gpu-security.ui"
)
class BootcDefaultGpuSecurity(Adw.Bin):
    """Step recording the GPU profile, NVIDIA consent and signature policy.

    Attributes:
        btn_next: Button advancing to the next step.
        usage_row: Row selecting the GPU usage profile.
        eula_group: Group holding the NVIDIA license widgets.
        eula_label: Label showing the license text.
        eula_entry: Entry where the user types the acceptance word.
        sig_switch: Switch enforcing module signature checks.
        error_label: Label shown when the helper refuses the choice.
    """

    __gtype_name__ = "BootcDefaultGpuSecurity"

    btn_next = Gtk.Template.Child()
    usage_row = Gtk.Template.Child()
    eula_group = Gtk.Template.Child()
    eula_label = Gtk.Template.Child()
    eula_entry = Gtk.Template.Child()
    sig_switch = Gtk.Template.Child()
    error_label = Gtk.Template.Child()

    def __init__(
        self,
        window: _Window,
        distro_info: object,
        key: str,
        step: object,
        **kwargs: object,
    ) -> None:
        """Build the GPU security step.

        Args:
            window: Installer window driving the step flow.
            distro_info: Distribution metadata handed by the window.
            key: Step key in the installer flow.
            step: Step descriptor handed by the window.
            **kwargs: GObject constructor properties.
        """
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.delta = False
        self.__accepted = False

        labels: dict[str, str] = {
            "auto": _("Automatic: use what the detected GPUs offer"),
            "gaming": _("Gaming and desktop"),
            "ia": _("AI and compute"),
        }
        self.usage_row.set_model(
            Gtk.StringList.new([labels[usage] for usage in gpu_config.USAGES])
        )
        _unused = self.usage_row.connect("notify::selected", self.__on_changed)
        _unused = self.eula_entry.connect("changed", self.__on_changed)
        _unused = self.btn_next.connect("clicked", self.__on_next)
        # The image is chosen on an earlier page: re-evaluate when shown.
        _unused = self.connect("map", self.__on_changed)
        self.__on_changed()

    def should_show(self, context: dict[str, object]) -> bool:
        """Tell whether the step is shown.

        Args:
            context: Installer context.

        Returns:
            Always True: the step is unconditional.
        """
        return True

    def test_auto_advance(self) -> None:
        """Click the next button, as the automated test expects."""
        self.btn_next.emit("clicked")

    def __usage(self) -> str:
        return gpu_config.USAGES[self.usage_row.get_selected()]

    def __recipe(self) -> dict[str, object] | None:
        return cast(
            "dict[str, object] | None",
            getattr(self.__window, "recipe", None),
        )

    def __imgref(self) -> str:
        image_step = getattr(self.__window, "image_step", None)
        finals = (
            cast(_FinalsProvider, image_step).get_finals()
            if image_step is not None else None
        )
        return gpu_config.selected_imgref(finals, self.__recipe())

    def __needs_eula(self) -> bool:
        return gpu_config.eula_required(self.__recipe(), self.__imgref())

    def __on_changed(self, *args: object) -> None:
        needs = self.__needs_eula()
        if needs and not self.eula_label.get_text():
            self.eula_label.set_text(gpu_config.eula_text())
        self.eula_group.set_visible(needs)
        ok = not needs or gpu_config.eula_accepted(self.eula_entry.get_text())
        if needs and not ok:
            self.eula_entry.add_css_class("error")
        else:
            self.eula_entry.remove_css_class("error")
        self.btn_next.set_sensitive(ok)

    def __on_next(self, *args: object) -> None:
        self.__accepted = self.__needs_eula()
        if not gpu_config.stage_choice(
            self.__usage(), self.__accepted, self.__imgref()
        ):
            self.error_label.set_visible(True)
            return
        self.error_label.set_visible(False)
        self.__window.next()

    def get_finals(self) -> dict[str, object]:
        """Return the step result merged into the finals.

        Returns:
            The gpu entry with the usage, consent and signature choices.
        """
        return {
            "gpu": {
                "usage": self.__usage(),
                "nvidiaConsent": self.__accepted,
                "sigEnforce": self.sig_switch.get_active(),
            }
        }
