# Build every layout in layouts/ via the screw-organiser CLI.
#
#   make                  all layouts as multi-material 3MFs -> out/
#   make stl              all layouts as single combined STLs
#   make stackable        all layouts with the stacking lip -> out/stackable/
#   make gridfinity       all layouts as Gridfinity modules (with magnets) [experimental]
#   make everything       all of the above
#   make <layout-name>    one layout's 3MF, e.g. make prusa-mmu3-upgrade
#   make clean            remove out/
#
# Outputs are only rebuilt when their layout or the generator source changes.
# Parallel builds work: make -j4 everything

LAYOUTS := $(basename $(notdir $(wildcard layouts/*.yaml)))
# example layouts stay out of the bulk targets; build them by name if needed
BUILDS  := $(filter-out example-%,$(LAYOUTS))
OUT     := out
RUN     := uv run screw-organiser
SRC     := $(shell find src -name '*.py') pyproject.toml
# extra CLI flags for every build, e.g. make EXTRA="--version-text v1.2"
EXTRA   ?=

.PHONY: all stl stackable gridfinity everything clean $(LAYOUTS)

all: $(addprefix $(OUT)/,$(addsuffix .3mf,$(BUILDS)))

stl: $(addprefix $(OUT)/,$(addsuffix .stl,$(BUILDS)))

stackable: $(addprefix $(OUT)/stackable/,$(addsuffix .3mf,$(BUILDS)))

gridfinity: $(addprefix $(OUT)/gridfinity/,$(addsuffix .3mf,$(BUILDS)))

everything: all stl stackable gridfinity

# convenience: `make prusa-mmu3-upgrade`
$(LAYOUTS): %: $(OUT)/%.3mf

$(OUT)/%.3mf: layouts/%.yaml $(SRC)
	$(RUN) --config $< --out $(OUT) $(EXTRA)

$(OUT)/%.stl: layouts/%.yaml $(SRC)
	$(RUN) --config $< --format stl --out $(OUT) $(EXTRA)

$(OUT)/stackable/%.3mf: layouts/%.yaml $(SRC)
	$(RUN) --config $< --stackable --out $(OUT)/stackable $(EXTRA)

$(OUT)/gridfinity/%.3mf: layouts/%.yaml $(SRC)
	$(RUN) --config $< --gridfinity --magnets --out $(OUT)/gridfinity $(EXTRA)

clean:
	rm -rf $(OUT)
