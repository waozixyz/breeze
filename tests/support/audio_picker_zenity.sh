#!/bin/sh
filter=
save=false
overwrite=false
filename=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --file-filter)
            shift
            filter=$1
            ;;
        --save)
            save=true
            ;;
        --confirm-overwrite)
            overwrite=true
            ;;
        --filename)
            shift
            filename=$1
            ;;
    esac
    shift
done

case "$PICKER_SCENARIO" in
    data)
        test "$filter" = 'Data files | *.zip *.json' || exit 2
        test "$save" = false || exit 2
        printf '%s\r\n' '/tmp/data file.zip'
        exit 0
        ;;
    save)
        test "$save" = true || exit 2
        test "$overwrite" = true || exit 2
        test "$filename" = 'backup ; literal.zip' || exit 2
        printf '%s\n' '/tmp/backup ; literal.zip'
        exit 0
        ;;
    empty)
        printf '\n'
        exit 0
        ;;
    signal)
        kill -TERM "$$"
        ;;
    music)
        case "$filter" in
            *'*.mp3'*) printf '%s\n' '/tmp/custom song.ogg'; exit 0 ;;
        esac
        exit 2
        ;;
    sound)
        case "$filter" in
            *'*.qoa'*)
                case "$filter" in
                    *'*.mp3'*) exit 2 ;;
                esac
                printf '%s\n' '/tmp/cue.wav'
                exit 0
                ;;
        esac
        exit 2
        ;;
    cancel)
        exit 1
        ;;
    unavailable)
        exit 127
        ;;
    overflow)
        printf '%s\n' '/tmp/a-very-long-audio-file-name-that-exceeds-the-small-test-buffer.ogg'
        exit 0
        ;;
esac
exit 2
