# The desktop benchmark (tests/desktop_benchmark.zi), which measures the Linux
# desktop build the same way before and after a change of desktop host. Its
# runtime scenario needs an executable built with the test driver:
#
#   build-queue -- make native KRYON_TEST_DRIVER=1
#   build-queue -- make desktop-benchmark BENCHMARK_LABEL=before
#   build-queue -- make desktop-benchmark-build BENCHMARK_LABEL=before
#
# Results go to build/desktop-benchmark/LABEL/ as Markdown and TSV.

DESKTOP_BENCHMARK_DIR := $(BUILD_DIR)/desktop-benchmark
DESKTOP_BENCHMARK := $(DESKTOP_BENCHMARK_DIR)/desktop-benchmark
DESKTOP_BENCHMARK_SOURCES := $(wildcard tests/desktop_benchmark*.zi) \
	$(KRYON_DIR)/src/backend/test_driver_client.zi
BENCHMARK_RUNS ?= 5
BENCHMARK_LABEL ?= current
BENCHMARK_OUT := $(abspath $(DESKTOP_BENCHMARK_DIR)/$(BENCHMARK_LABEL))

$(DESKTOP_BENCHMARK): $(DESKTOP_BENCHMARK_SOURCES) $(ZIRAN_BIN) $(SQLITE_AMALGAMATION_C)
	rm -rf $(DESKTOP_BENCHMARK_DIR)/c
	mkdir -p $(DESKTOP_BENCHMARK_DIR)/c
	$(ZIRAN_BIN) build --target=c --root tests --module-path $(KRYON_DIR)/src/backend \
		--module-path $(ZIRAN_DIR)/std -o $(DESKTOP_BENCHMARK_DIR)/c tests/desktop_benchmark.zi
	$(CC) -O1 -w -c -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION \
		$(SQLITE_AMALGAMATION_C) -o $(DESKTOP_BENCHMARK_DIR)/sqlite3.o
	$(CC) -O2 -I$(ZIRAN_DIR)/include -I$(DESKTOP_BENCHMARK_DIR)/c \
		$$(find $(DESKTOP_BENCHMARK_DIR)/c -name '*.c' | LC_ALL=C sort) \
		$(DESKTOP_BENCHMARK_DIR)/sqlite3.o -lm -o $@

.PHONY: desktop-benchmark-tool desktop-benchmark desktop-benchmark-build
desktop-benchmark-tool: $(DESKTOP_BENCHMARK)

desktop-benchmark: $(DESKTOP_BENCHMARK)
	@test -x $(TARGET) || { echo "Build the app first: KRYON_TEST_DRIVER=1 make native" >&2; exit 1; }
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		-u SESSION_MANAGER -u GDK_DISPLAY YUE_DESKTOP_RECOVERY=0 \
		$(DESKTOP_BENCHMARK) run $(abspath $(TARGET)) $(CURDIR) $(BENCHMARK_OUT) $(BENCHMARK_RUNS)

desktop-benchmark-build: $(DESKTOP_BENCHMARK)
	$(DESKTOP_BENCHMARK) build $(CURDIR) $(BENCHMARK_OUT) $(BENCHMARK_RUNS)
