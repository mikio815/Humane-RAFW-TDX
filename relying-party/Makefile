CC = gcc
CFLAGS = -fPIC -O2
LDFLAGS = -shared -lsgx_dcap_quoteverify

TARGET = libqvlwrapper.so
SRC = qvl_wrapper.c

VENV_PYTHON = ./venv/bin/python3
RP_SCRIPT = rp_client.py

.PHONY: all build run clean

all: build run

build: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)
	@echo "Built: $(TARGET)"

run:
	$(VENV_PYTHON) $(RP_SCRIPT)

clean:
	rm -f $(TARGET) ima_runtime_measurements.txt tdeventlog.txt
