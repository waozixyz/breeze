# F-Droid builds

`F-Droid security and clean build` uses the official F-Droid buildserver
container, the recipe in `packaging/fdroid-build.json`, and the real
`fdroid build --scan-binary` command. It runs on pull requests, master pushes
and a daily schedule. It starts with an empty Ziran source cache, so an
unpublished or unreachable dependency pin fails even if other builders have
an older cached copy.

The generated metadata takes the full source commit, version and Android
versionCode from the current candidate. F-Droid performs its normal source
cleaning, signing-configuration removal, source scan, unsigned universal
release build, APK metadata validation and binary scan. No scanner error is
ignored. The job retains its APK, metadata and logs as `fdroid-unsigned`.

Before the release workflow can publish, `Verify F-Droid reproducibility`
checks the signed F-Droid APK against the allowed signing certificate, then
uses `apksigcopier compare --unsigned` to verify that its signature also
validates the independently rebuilt APK. A mismatch blocks publication.

These checks run without signing credentials. The ordinary Android release
job alone receives the signing key.

## The 2.1.34 failure

[fdroiddata!53430](https://gitlab.com/fdroid/fdroiddata/-/merge_requests/53430)
failed in [the dependency preparation step](https://gitlab.com/fdroid/checkupdates-bot-fdroiddata/-/jobs/17306590795).
Its OQS pin, `5cc7677b290f0448462410f7c7e85f518664b943`, was no longer
reachable from the repository's advertised history after a history rewrite.
A fresh clone failed with `fatal: unable to read tree`, before Gradle ran.
The current lock pins the replacement history. Never rewrite public package
history after an application has released a lock referring to it.

The upstream F-Droid entry must use the full commit of a successfully
published release and its corresponding `inbe-VERSION-fdroid.apk` binary.
A passing GitHub check does not mean F-Droid has merged or distributed that
release; verify its own pipeline and publication separately.

## Local verification

F-Droid resets and cleans the source checkout. Never run it against the
owner's real checkout. `scripts/check-fdroid.py` only accepts a disposable
Actions checkout or a private Podman overlay mounted at
`WORKSPACE/build/xyz.waozi.inbe`. It refuses an ordinary checkout before
running Git or modifying any files.
