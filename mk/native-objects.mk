# Compiles every native C source to its own object so a rebuild recompiles
# only sources whose code, headers, or flags changed, and runs in parallel.
# The main Makefile writes $(OBJ_DIR)/inputs.mk (NATIVE_SOURCES and
# NATIVE_CFLAGS) and runs this file with -f; objects mirror each source's
# absolute path under $(OBJ_DIR), and the link reads $(OBJ_DIR)/objects.rsp.

OBJ_DIR ?= build/obj/native
include $(OBJ_DIR)/inputs.mk

NATIVE_OBJECTS := $(foreach source,$(NATIVE_SOURCES),$(OBJ_DIR)$(abspath $(source:.c=.o)))
FLAGS_STAMP := $(OBJ_DIR)/cflags.txt

.PHONY: all
all: $(NATIVE_OBJECTS)
	$(file >$(OBJ_DIR)/objects.rsp,$(NATIVE_OBJECTS))

# Rewrite the flags record only when the flags change, so a flag change
# recompiles everything and an unchanged build recompiles nothing.
$(FLAGS_STAMP): FORCE
	@mkdir -p $(dir $@)
	@printf '%s\n' '$(subst ','"'"',$(NATIVE_CFLAGS))' > $@.new
	@if cmp -s $@.new $@; then rm -f $@.new; else mv $@.new $@; fi

$(OBJ_DIR)/%.o: /%.c $(FLAGS_STAMP)
	@mkdir -p $(dir $@)
	@printf '  CC %s\n' '$<'
	@$(CC) $(NATIVE_CFLAGS) -MMD -MP -c '$<' -o '$@'

.PHONY: FORCE
FORCE:

-include $(NATIVE_OBJECTS:.o=.d)
