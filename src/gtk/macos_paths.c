/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <mach-o/dyld.h>
#include <limits.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static pthread_once_t paths_once = PTHREAD_ONCE_INIT;
static char data_path[PATH_MAX];
static char locale_path[PATH_MAX];

static void initialize_paths(void)
{
    char executable[PATH_MAX], resolved[PATH_MAX];
    uint32_t size = sizeof(executable);
    if (_NSGetExecutablePath(executable, &size) != 0 ||
        realpath(executable, resolved) == NULL)
        return;
    char *slash = strrchr(resolved, '/');
    if (!slash)
        return;
    *slash = '\0';
    /* Only an actual Contents/MacOS layout activates bundle lookup. */
    const char *suffix = "/Contents/MacOS";
    size_t length = strlen(resolved), suffix_length = strlen(suffix);
    if (length < suffix_length || strcmp(resolved + length - suffix_length, suffix))
        return;
    resolved[length - strlen("/MacOS")] = '\0';
    int count = snprintf(data_path, sizeof(data_path), "%s/Resources/share/xiphos", resolved);
    if (count < 0 || (size_t)count >= sizeof(data_path))
        data_path[0] = '\0';
    count = snprintf(locale_path, sizeof(locale_path), "%s/Resources/share/locale", resolved);
    if (count < 0 || (size_t)count >= sizeof(locale_path))
        locale_path[0] = '\0';
}

const char *xiphos_macos_resource_dir(int locale, const char *fallback)
{
    pthread_once(&paths_once, initialize_paths);
    const char *path = locale ? locale_path : data_path;
    struct stat info;
    if (*path && stat(path, &info) == 0 && S_ISDIR(info.st_mode))
        return path;
    return fallback;
}
