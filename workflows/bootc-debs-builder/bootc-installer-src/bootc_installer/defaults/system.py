# system.py
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

from bootc_installer.utils import locale_config
from bootc_installer.utils.system_config import valid_hostname, valid_root_password


@Gtk.Template(resource_path="/org/bootcinstaller/Installer/gtk/default-system.ui")
class BootcDefaultSystem(Adw.Bin):
    __gtype_name__ = "BootcDefaultSystem"

    btn_next = Gtk.Template.Child()
    locale_group = Gtk.Template.Child()
    locale_row = Gtk.Template.Child()
    keyboard_row = Gtk.Template.Child()
    hostname_entry = Gtk.Template.Child()
    root_password_entry = Gtk.Template.Child()
    root_password_confirmation = Gtk.Template.Child()
    sudo_switch = Gtk.Template.Child()
    ssh_root_switch = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.delta = False

        # The first row of each list keeps the image default; the others come
        # from what the live system ships, and the group is hidden when it
        # offers nothing.
        self.__locales = locale_config.supported_locales()
        self.__keyboards = locale_config.keyboard_layouts()
        self.locale_row.set_model(Gtk.StringList.new(
            [_("Image default")] + self.__locales))
        self.keyboard_row.set_model(Gtk.StringList.new(
            [_("Image default")] + [k[2] for k in self.__keyboards]))
        self.locale_group.set_visible(bool(self.__locales or self.__keyboards))
        self.locale_row.set_visible(bool(self.__locales))
        self.keyboard_row.set_visible(bool(self.__keyboards))

        for row in (self.hostname_entry, self.root_password_entry,
                    self.root_password_confirmation):
            row.connect("changed", self.__on_field_changed)
        self.btn_next.connect("clicked", self.__window.next)
        self.__on_field_changed()

    def should_show(self, context: dict) -> bool:
        return True

    def test_auto_advance(self):
        self.btn_next.emit("clicked")

    def __hostname_ok(self) -> bool:
        # Empty keeps the hardware-derived hostname chosen by the installer.
        text = self.hostname_entry.get_text().strip()
        return not text or valid_hostname(text)

    def __on_field_changed(self, *args):
        hostname_ok = self.__hostname_ok()
        passwords_ok = valid_root_password(
            self.root_password_entry.get_text(),
            self.root_password_confirmation.get_text(),
        )
        for widget, ok in ((self.hostname_entry, hostname_ok),
                           (self.root_password_confirmation, passwords_ok)):
            if ok:
                widget.remove_css_class("error")
            else:
                widget.add_css_class("error")
        self.btn_next.set_sensitive(hostname_ok and passwords_ok)

    def get_finals(self):
        finals = {
            "system": {
                "rootPassword": self.root_password_entry.get_text(),
                "sudo": self.sudo_switch.get_active(),
                "sshRootLogin": self.ssh_root_switch.get_active(),
            }
        }
        locale_index = self.locale_row.get_selected()
        if locale_index > 0:
            finals["system"]["locale"] = self.__locales[locale_index - 1]
        keyboard_index = self.keyboard_row.get_selected()
        if keyboard_index > 0:
            layout, variant, _description = self.__keyboards[keyboard_index - 1]
            finals["system"]["keyboard"] = {
                "model": locale_config.DEFAULT_MODEL,
                "layout": layout,
                "variant": variant,
            }
        hostname = self.hostname_entry.get_text().strip()
        if hostname:
            finals["hostname"] = hostname
        return finals
