# gpu_security.py
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gettext import gettext as _

from gi.repository import Adw, Gtk

from bootc_installer.utils import gpu_config


@Gtk.Template(resource_path="/org/bootcinstaller/Installer/gtk/default-gpu-security.ui")
class BootcDefaultGpuSecurity(Adw.Bin):
    __gtype_name__ = "BootcDefaultGpuSecurity"

    btn_next = Gtk.Template.Child()
    usage_row = Gtk.Template.Child()
    eula_group = Gtk.Template.Child()
    eula_label = Gtk.Template.Child()
    eula_entry = Gtk.Template.Child()
    sig_switch = Gtk.Template.Child()
    error_label = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.delta = False
        self.__accepted = False

        labels = {
            "auto": _("Automatic: use what the detected GPUs offer"),
            "gaming": _("Gaming and desktop"),
            "ia": _("AI and compute"),
        }
        self.usage_row.set_model(
            Gtk.StringList.new([labels[u] for u in gpu_config.USAGES])
        )
        self.usage_row.connect("notify::selected", self.__on_changed)
        self.eula_entry.connect("changed", self.__on_changed)
        self.btn_next.connect("clicked", self.__on_next)
        # The image is chosen on an earlier page: re-evaluate when shown.
        self.connect("map", self.__on_changed)
        self.__on_changed()

    def should_show(self, context: dict) -> bool:
        return True

    def test_auto_advance(self):
        self.btn_next.emit("clicked")

    def __usage(self) -> str:
        return gpu_config.USAGES[self.usage_row.get_selected()]

    def __imgref(self) -> str:
        image_step = getattr(self.__window, "image_step", None)
        finals = image_step.get_finals() if image_step else None
        return gpu_config.selected_imgref(
            finals, getattr(self.__window, "recipe", None)
        )

    def __needs_eula(self) -> bool:
        return gpu_config.eula_required(
            getattr(self.__window, "recipe", None), self.__imgref()
        )

    def __on_changed(self, *args):
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

    def __on_next(self, *args):
        self.__accepted = self.__needs_eula()
        if not gpu_config.stage_choice(
            self.__usage(), self.__accepted, self.__imgref()
        ):
            self.error_label.set_visible(True)
            return
        self.error_label.set_visible(False)
        self.__window.next()

    def get_finals(self):
        return {
            "gpu": {
                "usage": self.__usage(),
                "nvidiaConsent": self.__accepted,
                "sigEnforce": self.sig_switch.get_active(),
            }
        }
