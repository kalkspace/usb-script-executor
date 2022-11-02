#!/usr/bin/python3
from gi.repository import GLib

import dbus
import dbus.mainloop.glib
import os
from dbus.mainloop.glib import DBusGMainLoop
import click
import logging


def interface_added(system_bus, script, object_path, props):
    logging.debug(f"{object_path} was added")
    if (
        "org.freedesktop.UDisks2.Filesystem" in props
        and "org.freedesktop.UDisks2.Block" in props
    ):
        block = props["org.freedesktop.UDisks2.Block"]
        if not "Drive" in block:
            logging.debug(f"Object {object_path} doesn't have a drive property")
            return

        drive_path = block["Drive"]
        logging.debug(f"drive {drive_path} was added")
        drive = system_bus.get_object(
            "org.freedesktop.UDisks2",
            drive_path,
        )
        properties_manager = dbus.Interface(drive, "org.freedesktop.DBus.Properties")
        ejectable = bool(
            properties_manager.Get("org.freedesktop.UDisks2.Drive", "Ejectable")
        )
        if not ejectable:
            logging.warning(
                f"drive {drive_path} is not ejectable. not an usb-stick? ignoring."
            )

        obj = system_bus.get_object(
            "org.freedesktop.UDisks2",
            object_path,
        )
        mount_path = obj.Mount({}, dbus_interface="org.freedesktop.UDisks2.Filesystem")
        logging.info(f"Mounted {object_path} to {mount_path}")
        cwd = os.getcwd()
        os.chdir(mount_path)
        result = os.system(" ".join(script))
        if result != 0:
            logging.error(f"script returned with error code {result}")
        os.chdir(cwd)
        obj.Unmount({}, dbus_interface="org.freedesktop.UDisks2.Filesystem")


@click.command()
@click.option("--debug", is_flag=True)
@click.argument("script", nargs=-1, required=True)
def main(debug, script):
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    DBusGMainLoop(set_as_default=True)
    system_bus = dbus.SystemBus()

    udisk_proxy = system_bus.get_object(
        "org.freedesktop.UDisks2", "/org/freedesktop/UDisks2"
    )
    udisk_proxy.connect_to_signal(
        "InterfacesAdded",
        lambda object_path, props: interface_added(
            system_bus, script, object_path, props
        ),
    )

    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()
