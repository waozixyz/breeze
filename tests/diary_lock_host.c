#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern bool diary_store_DiaryStorePrepare(void);
extern void diary_store_DiaryStoreClose(void);

bool ModuleTestDiaryLockInheritance(void)
{
    assert(diary_store_DiaryStorePrepare());
    int status[2];
    assert(pipe(status) == 0);
    assert(fcntl(status[1], F_SETFD, FD_CLOEXEC) == 0);
    pid_t child = fork();
    assert(child >= 0);
    if(child == 0) {
        close(status[0]);
        /* Match download/picker helpers: exec without closing the parent's
         * unrelated descriptors. EOF on status proves exec has completed. */
        execl("/bin/sleep", "sleep", "30", (char *)NULL);
        int error = errno;
        (void)write(status[1], &error, sizeof(error));
        _exit(127);
    }
    close(status[1]);
    int error = 0;
    ssize_t count;
    do {
        count = read(status[0], &error, sizeof(error));
    } while(count < 0 && errno == EINTR);
    close(status[0]);
    assert(count == 0);
    int result;
    assert(waitpid(child, &result, WNOHANG) == 0);

    /* The next app must reopen Diary even while the previous app's helper
     * remains alive. The real store performs both lock acquisitions. */
    diary_store_DiaryStoreClose();
    bool reopened = diary_store_DiaryStorePrepare();
    assert(kill(child, SIGKILL) == 0);
    assert(waitpid(child, &result, 0) == child);
    assert(diary_store_DiaryStorePrepare());
    if(!reopened) {
        fputs("Diary lock survived in an exec'd helper after the app closed\n", stderr);
    }
    return reopened;
}
