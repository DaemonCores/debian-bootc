# autoupdate.py
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

from gi.repository import Adw, Gtk


@Gtk.Template(resource_path="/org/bootcinstaller/Installer/gtk/default-autoupdate.ui")
class BootcDefaultAutoupdate(Adw.Bin):
    __gtype_name__ = "BootcDefaultAutoupdate"

    btn_next = Gtk.Template.Child()
    page_header = Gtk.Template.Child()
    autoupdate_switch = Gtk.Template.Child()

    def __init__(self, window, distro_info, key, step, **kwargs):
        super().__init__(**kwargs)
        self.__window = window
        self.__distro_info = distro_info
        self.__key = key
        self.__step = step
        self.delta = False

        self.btn_next.connect("clicked", self.__window.next)

    def should_show(self, context: dict) -> bool:
        return True

    def test_auto_advance(self):
        self.btn_next.emit("clicked")

    def get_finals(self):
        return {"autoupdate": {"enabled": self.autoupdate_switch.get_active()}}
