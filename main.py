import os
import subprocess
import re
import gi
import gettext
import locale

gi.require_version('Gtk', '4.0')  # Ensure GTK 4 is used
gi.require_version('Adw', '1')   # Ensure Adw version 1 is used
from gi.repository import Gtk, Adw

textdomain = "uefibma"

locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain(textdomain, "/usr/local/share/locale")
gettext.textdomain(textdomain)
_ = gettext.gettext

template = _("Will boot next time: {description}")
title = _("UEFI Boot Manager App")

class UEFIBootManager(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title(title)
        self.set_default_size(400, 200)

        # Layout container with margin
        win = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        
        # Create a header bar using Adw.HeaderBar for a modern look
        header_bar = Adw.HeaderBar()
        header_bar.set_show_title(title)
        header_bar.set_show_end_title_buttons(True)
        win.append(header_bar)  # Adw.ApplicationWindow allows setting a titlebar directly

        self.reboot_button = Gtk.Button(label=_("Reboot"))
        self.reboot_button.connect("clicked", self.on_reboot_clicked)
        header_bar.pack_end(self.reboot_button)

        # Label for showing selected boot next information
        self.boot_next_label = Gtk.Label(label=template.format(description=_("N/A")))
        content.append(self.boot_next_label)

        # Create and fill the list store
        self.liststore = Gtk.ListStore(str, str)
        self.update_boot_order()

        # Creating the TreeView
        treeview = Gtk.TreeView(model=self.liststore)
        treeview.connect("row-activated", self.on_row_activated)
        
        # Creating two columns
        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn(title=_("Boot Number"), cell_renderer=renderer_text, text=0)
        treeview.append_column(column_text)

        column_text = Gtk.TreeViewColumn(title=_("Description"), cell_renderer=renderer_text, text=1)
        treeview.append_column(column_text)
        

        # Adding treeview to the main window
        content.append(treeview)
        win.append(content)
        self.set_content(win)
        
    def on_reboot_clicked(self, button):
        subprocess.run(['pkexec', '/sbin/reboot'], capture_output=False)

    def update_boot_order(self):
        # Run efibootmgr and capture its output
        result = subprocess.run(['pkexec', '/usr/sbin/efibootmgr'], capture_output=True, text=True)
        if result.returncode == 0:
            boot_info = result.stdout
            self.parse_efibootmgr_output(boot_info)

    def on_row_activated(self, tree_view, path, column):
        model = tree_view.get_model()
        boot_num, description = model[path]
        subprocess.run(['pkexec', '/usr/sbin/efibootmgr', '-n', boot_num[0:4]], capture_output=False)
        self.boot_next_label.set_text(template.format(description=description))

    def parse_efibootmgr_output(self, output):
        self.liststore.clear()
        
        boot_entry_pattern = re.compile(r'Boot([0-9A-Fa-f]{4})\*?\s+(.+)(?=\sBBS|\sPciRoot|\sVenHw|\sHD)')

        for line in output.splitlines():
            match = boot_entry_pattern.search(line)
            if match:
                boot_num, description = match.groups()
                self.liststore.append([boot_num, description])
        
        # Find current boot and boot order
        current_boot = re.search(r'BootCurrent: (\d+)', output)
        if current_boot:
            current_boot = current_boot.group(1)
        
        next_boot = re.search(r'BootNext: (\d+)', output)
        if next_boot:
            next_boot = next_boot.group(1)
            self.boot_next_label.set_text(template.format(description=self.liststore[int(next_boot, 16)][1]))
        else:
            current_boot_index = int(current_boot, 16)
            if current_boot_index < len(self.liststore):
                self.boot_next_label.set_text(template.format(description=self.liststore[int(current_boot_index, 16)][1]))


class UEFIBootManagerApp(Adw.Application):
    def __init__(self):
        super().__init__()

    def do_activate(self):
        win = UEFIBootManager(self)
        win.present()

def main():
    app = UEFIBootManagerApp()
    app.run(None)

if __name__ == "__main__":
    main()