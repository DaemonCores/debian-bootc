"""Automatic-update step of the bootc installer.

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

from typing import Protocol

from gi.repository import (  # pyright: ignore[reportMissingModuleSource]
    Adw,
    Gtk,
)


class _Window(Protocol):
    """The upstream installer window this step drives."""

    def next(self) -> None:
        """Advance to the next installer step."""


@Gtk.Template(
    resource_path="/org/bootcinstaller/Installer/gtk/default-autoupdate.ui"
)
class BootcDefaultAutoupdate(Adw.Bin):
    """Step that records whether automatic updates are enabled.

    Attributes:
        btn_next: Button advancing to the next step.
        page_header: Header of the automatic-update page.
        autoupdate_switch: Switch enabling automatic updates.
    """

    __gtype_name__ = "BootcDefaultAutoupdate"

    btn_next = Gtk.Template.Child()
    page_header = Gtk.Template.Child()
    autoupdate_switch = Gtk.Template.Child()

    def __init__(
        self,
        window: _Window,
        distro_info: object,
        key: str,
        step: object,
        **kwargs: object,
    ) -> None:
        """Build the automatic-update step.

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

        _ = self.btn_next.connect("clicked", self.__window.next)

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

    def get_finals(self) -> dict[str, object]:
        """Return the step result merged into the finals.

        Returns:
            The ``autoupdate`` entry with the switch state.
        """
        return {"autoupdate": {"enabled": self.autoupdate_switch.get_active()}}
