CC = gcc
CFLAGS = -fPIC -O2
LDFLAGS = -shared -ltdx_attest

TARGET_SO = libtdxwrapper.so
SRC = tdx_wrapper.c

VENV := $(CURDIR)/venv
PYTHON := $(VENV)/bin/python3
PYINSTALLER := $(VENV)/bin/pyinstaller

ATT_BIN = attester
DIST_DIR = dist

.PHONY: all build_so build_attester run clean

all: build_so build_attester run

build_so: $(TARGET_SO)

$(TARGET_SO): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)
	@echo "Built: $(TARGET_SO)"

build_attester:
	$(PYINSTALLER) \
		--onefile \
		--name $(ATT_BIN) \
		api.py
	@echo "Built Attester binary: $(DIST_DIR)/$(ATT_BIN)"

run:
	./$(DIST_DIR)/$(ATT_BIN)

clean:
	rm -rf $(TARGET_SO) build dist *.spec tls_cert.pem tls_key.pem
