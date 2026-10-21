/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "macos_tts.h"
int main(void)
{
    if (macos_tts_speak(0, "test", 4) != 0)
        return 1;
    if (macos_tts_speak(0, 0, -1) != 0)
        return 2;
    macos_tts_cancel(0);
    macos_tts_destroy(0);
    return 0;
}
