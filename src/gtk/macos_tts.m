/* macOS read-aloud adapter. SPDX-License-Identifier: GPL-2.0-or-later */
#import <AVFoundation/AVFoundation.h>
#include "macos_tts.h"

/* This translation unit uses manual reference counting. AVSpeechSynthesizer
 * keeps the existing speak/cancel behavior without a shell or child process.
 * Speech is queued asynchronously on the GTK main thread. */
void *macos_tts_create(void)
{
    @autoreleasepool {
        return [[AVSpeechSynthesizer alloc] init];
    }
}

void macos_tts_cancel(void *handle)
{
    @autoreleasepool {
        [(AVSpeechSynthesizer *)handle stopSpeakingAtBoundary:AVSpeechBoundaryImmediate];
    }
}

void macos_tts_destroy(void *handle)
{
    @autoreleasepool {
        macos_tts_cancel(handle);
        [(AVSpeechSynthesizer *)handle release];
    }
}

int macos_tts_speak(void *handle, const char *text, int length)
{
    if (!handle || !text || length <= 0)
        return 0;
    @autoreleasepool {
        NSString *utterance = [[NSString alloc] initWithBytes:text
                                                    length:(NSUInteger)length
                                                  encoding:NSUTF8StringEncoding];
        if (!utterance)
            return 0;
        AVSpeechSynthesizer *synth = (AVSpeechSynthesizer *)handle;
        [synth stopSpeakingAtBoundary:AVSpeechBoundaryImmediate];
        AVSpeechUtterance *speech = [[AVSpeechUtterance alloc] initWithString:utterance];
        [synth speakUtterance:speech];
        [speech release];
        [utterance release];
        return 1;
    }
}
