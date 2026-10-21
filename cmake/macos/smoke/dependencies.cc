// SPDX-License-Identifier: GPL-2.0-or-later
#include <biblesync.hh>
#include <swbuf.h>
#include <gdk/gdkkeysyms.h>
#include <libintl.h>
#include <uuid/uuid.h>
#include <cstring>
#include <iostream>

int main()
{
    uuid_t id;
    char formatted[37];
    uuid_generate(id);
    uuid_unparse(id, formatted);
    if (std::strlen(formatted) != 36)
        return 1;
    BibleSync sync("Xiphos build check", "1", "test");
    if (sync.getMode() != BSP_MODE_DISABLE || sync.getVersion().empty())
        return 2;
    // Exercise gettext's external library, not merely its header.
    if (std::strcmp(dgettext("xiphos-build-check", "test"), "test"))
        return 3;
    sword::SWBuf text("test");
    if (std::strcmp(text.c_str(), "test"))
        return 4;
    if (GDK_KEY_Shift_L != 0xffe1 || GDK_KEY_F1 != 0xffbe)
        return 5;
    std::cout << "UUID, gettext, SWORD, GTK keysyms, BibleSync "
              << sync.getVersion() << " passed (network disabled)\n";
    return 0;
}
