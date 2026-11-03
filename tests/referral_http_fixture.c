/* Test-only transport substitution for owned native referral UI processes.
 * The real client retains its canonical issuer and signs production requests.
 * Only curl's final transport URL is mapped to a private test-only Daochi.
 * Every other destination fails closed; this library is never packaged.
 */
#define _GNU_SOURCE
#include <curl/curl.h>
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#undef curl_easy_setopt

#ifdef REFERRAL_STATIC_CURL
extern CURLcode __real_curl_easy_setopt(CURL *, CURLoption, ...);
#define FIXTURE_SETOPT __wrap_curl_easy_setopt
#else
#define FIXTURE_SETOPT curl_easy_setopt
#endif
CURLcode FIXTURE_SETOPT(CURL *handle, CURLoption option, ...) {
#ifdef REFERRAL_STATIC_CURL
    CURLcode (*real_setopt)(CURL *, CURLoption, ...) = __real_curl_easy_setopt;
#else
    CURLcode (*real_setopt)(CURL *, CURLoption, ...) = dlsym(RTLD_NEXT, "curl_easy_setopt");
#endif
    if (!real_setopt) return CURLE_FAILED_INIT;
    va_list args;
    va_start(args, option);
    CURLcode result;
    if (option == CURLOPT_URL) {
        const char *url = va_arg(args, const char *);
        const char prefix[] = "https://api.waozi.xyz/";
        const char *target = getenv("REFERRAL_TEST_URL");
        char mapped[8192];
        if (!url || strncmp(url, prefix, sizeof(prefix)-1) || !target ||
            strncmp(target, "http://127.0.0.1:", 17) ||
            snprintf(mapped, sizeof(mapped), "%s/%s", target, url + sizeof(prefix)-1) >= (int)sizeof(mapped)) {
            result = CURLE_URL_MALFORMAT;
        } else {
            result = real_setopt(handle, option, mapped);
        }
    } else if (option < CURLOPTTYPE_OBJECTPOINT) {
        result = real_setopt(handle, option, va_arg(args, long));
    } else if (option < CURLOPTTYPE_FUNCTIONPOINT) {
        result = real_setopt(handle, option, va_arg(args, void *));
    } else if (option < CURLOPTTYPE_OFF_T) {
        result = real_setopt(handle, option, va_arg(args, void (*)(void)));
    } else if (option < CURLOPTTYPE_BLOB) {
        result = real_setopt(handle, option, va_arg(args, curl_off_t));
    } else {
        result = real_setopt(handle, option, va_arg(args, void *));
    }
    va_end(args);
    return result;
}
