ATT_DIR := ../../attester
SCRIPT  := reference_measurement.py

.PHONY: all build run clean

all: build run

build:
	$(MAKE) -C $(ATT_DIR) build_so build_attester

run:
	python3 $(SCRIPT)

clean:
	$(MAKE) -C $(ATT_DIR) clean
