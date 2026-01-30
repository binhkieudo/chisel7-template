# Cocotb Makefile for GCD Verification

# Simulator settings
SIM ?= verilator
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = $(PWD)/../../GCD.sv

# Top module
TOPLEVEL = GCD

# Python test module
MODULE = gcd_test

# Verilator specific flags - use FST for faster, smaller waveforms
EXTRA_ARGS += --trace --trace-structs
COMPILE_ARGS += -Wno-fatal

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim

# Clean target
clean::
	rm -rf __pycache__ sim_build results.xml *.vcd *.fst
