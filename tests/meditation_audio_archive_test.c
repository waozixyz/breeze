#include "practices/meditation/meditation_audio_archive.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    String archive = StringView(argv[1], strlen(argv[1]));
    String cache = StringView(argv[2], strlen(argv[2]));
    int expected = atoi(argv[3]);
    int actual = InstallMeditationAudioArchive(archive, cache);
    if ((expected == 3 && actual != 3) ||
        (expected == 0 && actual > 0)) {
        fprintf(stderr, "archive install: got %d, expected %d\n", actual, expected);
        return 1;
    }
    return 0;
}
