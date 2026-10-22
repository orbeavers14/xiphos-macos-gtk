/* SPDX-License-Identifier: GPL-2.0-or-later
 * Own a private authenticated X11 display and private D-Bus session. */
#include <mach-o/dyld.h>
#include <sys/stat.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <signal.h>
#include <limits.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static volatile sig_atomic_t stopping;
static void interrupted(int signal_number) { stopping = signal_number; }

static void resource_env(const char *name, const char *root, const char *relative)
{
    char *value = NULL;
    if (asprintf(&value, "%s/%s", root, relative) < 0) exit(1);
    setenv(name, value, 1);
    free(value);
}

static void mkdir_parents(const char *directory)
{
    char path[PATH_MAX];
    if (strlen(directory) >= sizeof(path)) return;
    strcpy(path, directory);
    for (char *part = path + 1; *part; part++) {
        if (*part == '/') {
            *part = '\0'; mkdir(path, 0700); *part = '/';
        }
    }
    mkdir(path, 0700);
}

static pid_t launch(char *const args[], int ready_fd)
{
    pid_t child = fork();
    if (child == 0) {
        setpgid(0, 0);
        if (ready_fd >= 0 && ready_fd != 3) {
            dup2(ready_fd, 3);
            close(ready_fd);
        }
        if (ready_fd >= 0)
            fcntl(3, F_SETFD, 0);
        execv(args[0], args);
        perror(args[0]);
        _exit(127);
    }
    if (child > 0) setpgid(child, child);
    return child;
}

static void terminate_child(pid_t child)
{
    if (child <= 0)
        return;
    kill(-child, SIGTERM);
    for (int attempt = 0; attempt < 50; ++attempt) {
        if (waitpid(child, NULL, WNOHANG) != 0)
            return;
        usleep(100000);
    }
    kill(-child, SIGKILL);
    waitpid(child, NULL, 0);
}

int main(int argc, char **argv)
{
    if (argc >= 2 && !strcmp(argv[1], "--private-session-child")) {
        const char *address = getenv("DBUS_SESSION_BUS_ADDRESS");
        if (!address) return 1;
        fprintf(stderr, "Xiphos: private bus %s\n", address);
        argv[1] = "../MacOS/xiphos-bin";
        execv(argv[1], argv + 1);
        perror("xiphos-bin");
        return 127;
    }
    char executable[PATH_MAX], root[PATH_MAX];
    uint32_t length = sizeof(executable);
    if (_NSGetExecutablePath(executable, &length) || !realpath(executable, root))
        return 1;
    char *slash = strrchr(root, '/');
    if (!slash) return 1;
    *slash = '\0';
    if (chdir(root) || chdir("../Resources") || !getcwd(root, sizeof(root)))
        return 1;
    /* Paths remain relative to this directory in relocated vendor binaries. */
    setenv("XIPHOS_BUNDLE_ROOT", root, 1);
    resource_env("PATH", root, "runtime/bin:/usr/bin:/bin:/usr/sbin:/sbin");
    char *data_dirs = NULL;
    if (asprintf(&data_dirs, "%s/runtime/share:%s/share", root, root) < 0) return 1;
    setenv("XDG_DATA_DIRS", data_dirs, 1);
    free(data_dirs);
    resource_env("XDG_CONFIG_DIRS", root, "runtime/etc");
    resource_env("GSETTINGS_SCHEMA_DIR", root, "runtime/share/glib-2.0/schemas");
    resource_env("GIO_MODULE_DIR", root, "runtime/lib/gio/modules");
    resource_env("GDK_PIXBUF_MODULE_FILE", root, "runtime/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache");
    resource_env("FONTCONFIG_PATH", root, "runtime/etc/fonts");
    resource_env("FONTCONFIG_FILE", root, "runtime/etc/fonts/fonts.conf");
    resource_env("GTK_EXE_PREFIX", root, "runtime");
    resource_env("GTK_DATA_PREFIX", root, "runtime");
    resource_env("GST_PLUGIN_SYSTEM_PATH_1_0", root, "runtime/lib/gstreamer-1.0");
    resource_env("GST_PLUGIN_SCANNER", root, "runtime/libexec/gstreamer-1.0/gst-plugin-scanner");
    setenv("WEBKIT_DISABLE_COMPOSITING_MODE", "1", 1);
    setenv("LIBGL_ALWAYS_SOFTWARE", "1", 1);
    if (!getenv("LANG")) setenv("LANG", "en_US.UTF-8", 1);
    const char *home = getenv("HOME");
    if (home) {
        if (!getenv("XDG_CACHE_HOME"))
            resource_env("XDG_CACHE_HOME", home, "Library/Caches/Xiphos");
        char logs[PATH_MAX];
        const char *directories[] = {"Library", "Library/Logs", "Library/Logs/X11"};
        for (unsigned index = 0; index < sizeof(directories) / sizeof(directories[0]); index++) {
            int count = snprintf(logs, sizeof(logs), "%s/%s", home, directories[index]);
            if (count > 0 && (size_t)count < sizeof(logs)) mkdir(logs, 0700);
        }
    }
    const char *cache = getenv("XDG_CACHE_HOME");
    if (cache) {
        char *fonts_cache = NULL;
        if (asprintf(&fonts_cache, "%s/fontconfig", cache) < 0) return 1;
        mkdir_parents(fonts_cache);
        free(fonts_cache);
    }

    char temporary[] = "/private/tmp/xiphos-session-XXXXXX";
    if (!mkdtemp(temporary)) return 1;
    char authority[PATH_MAX], cookie[33], display[32], socket_path[128];
    snprintf(authority, sizeof(authority), "%s/Xauthority", temporary);
    int auth_fd = open(authority, O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (auth_fd < 0) { rmdir(temporary); return 1; }
    close(auth_fd);
    unsigned char random_bytes[16];
    arc4random_buf(random_bytes, sizeof(random_bytes));
    for (int index = 0; index < 16; index++)
        snprintf(cookie + 2 * index, 3, "%02x", random_bytes[index]);
    unsigned number;
    do {
        number = 100 + arc4random_uniform(900);
        snprintf(socket_path, sizeof(socket_path), "/private/tmp/.X11-unix/X%u", number);
    } while (access(socket_path, F_OK) == 0);
    snprintf(display, sizeof(display), ":%u", number);
    setenv("DISPLAY", display, 1);
    setenv("XAUTHORITY", authority, 1);
    char *auth_args[] = {"./runtime/bin/xauth", "-f", authority, "add", display,
                         "MIT-MAGIC-COOKIE-1", cookie, NULL};
    pid_t auth = launch(auth_args, -1);
    int status = 1;
    if (auth <= 0 || waitpid(auth, &status, 0) < 0 || status != 0) {
        unlink(authority); rmdir(temporary); return 1;
    }
    signal(SIGTERM, interrupted);
    signal(SIGINT, interrupted);
    signal(SIGHUP, interrupted);
    int ready[2];
    if (pipe(ready)) { unlink(authority); rmdir(temporary); return 1; }
    fcntl(ready[0], F_SETFD, FD_CLOEXEC);
    char fonts[PATH_MAX], keyboard[PATH_MAX];
    if (snprintf(fonts, sizeof(fonts), "%s/runtime/share/fonts/misc", root) >= (int)sizeof(fonts) ||
        snprintf(keyboard, sizeof(keyboard), "%s/runtime/share/X11/xkb", root) >= (int)sizeof(keyboard)) {
        close(ready[0]); close(ready[1]); unlink(authority); rmdir(temporary); return 1;
    }
    char *server_args[] = {"./X11.app/Contents/MacOS/X11.bin", display,
        "-auth", authority, "-nolisten", "tcp", "-iglx", "-noreset",
        "-displayfd", "3", "-fp", fonts, "-xkbdir", keyboard, NULL};
    pid_t server = launch(server_args, ready[1]);
    close(ready[1]);
    fd_set reads;
    FD_ZERO(&reads); FD_SET(ready[0], &reads);
    struct timeval timeout = {30, 0};
    char response[32] = {0};
    int available = select(ready[0] + 1, &reads, NULL, NULL, &timeout);
    ssize_t received = available > 0 ? read(ready[0], response, sizeof(response) - 1) : -1;
    close(ready[0]);
    pid_t app = -1;
    pid_t window_manager = -1;
    struct stat owned_socket;
    int have_socket = 0;
    int result = 1;
    if (!stopping && received > 0 && (unsigned)strtoul(response, NULL, 10) == number) {
        have_socket = lstat(socket_path, &owned_socket) == 0 && S_ISSOCK(owned_socket.st_mode);
        fprintf(stderr, "Xiphos: private display %s ready\n", display);
        char *wm_args[] = {"./runtime/bin/quartz-wm", NULL};
        window_manager = launch(wm_args, -1);
        char **app_args = calloc((size_t)argc + 6, sizeof(char *));
        if (app_args) {
            app_args[0] = "./runtime/bin/dbus-run-session";
            app_args[1] = "--config-file=./session.conf";
            app_args[2] = "--";
            app_args[3] = "../MacOS/Xiphos";
            app_args[4] = "--private-session-child";
            for (int index = 1; index < argc; index++)
                app_args[index + 4] = argv[index];
            app = launch(app_args, -1);
            free(app_args);
            while (!stopping && app > 0) {
                pid_t done = waitpid(app, &status, WNOHANG);
                if (done == app) {
                    app = -1;
                    result = WIFEXITED(status) ? WEXITSTATUS(status) : 1;
                    break;
                }
                if (done < 0) break;
                if (waitpid(server, NULL, WNOHANG) == server) {
                    server = -1;
                    break;
                }
                usleep(100000);
            }
        }
    } else {
        fprintf(stderr, "Xiphos: bundled X11 server did not become ready (received %zd bytes: %s)\n",
                received, response);
    }
    terminate_child(app);
    terminate_child(window_manager);
    terminate_child(server);
    /* XQuartz can leave its Unix socket after forced termination. Only remove
     * the same socket inode observed while our private server owned it. */
    struct stat remaining_socket;
    if (have_socket && lstat(socket_path, &remaining_socket) == 0 &&
        S_ISSOCK(remaining_socket.st_mode) &&
        remaining_socket.st_dev == owned_socket.st_dev &&
        remaining_socket.st_ino == owned_socket.st_ino)
        unlink(socket_path);
    unlink(authority);
    rmdir(temporary);
    return result;
}
