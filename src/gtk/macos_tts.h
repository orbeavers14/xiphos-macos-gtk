/* macOS read-aloud adapter. SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef XIPHOS_MACOS_TTS_H
#define XIPHOS_MACOS_TTS_H

/* Called on the GTK main thread. Text is UTF-8 with a byte length. */
void *macos_tts_create(void);
void macos_tts_destroy(void *handle);
int macos_tts_speak(void *handle, const char *text, int length);
void macos_tts_cancel(void *handle);

#endif
