# Makefile for Yosys Synthesis Flow with SKY130A PDK
# Provides automated synthesis, constraint generation, and reporting

# ============================================================================
# Configuration Variables
# ============================================================================

# PDK Configuration
export PDK_ROOT ?= /opt/pdk
export PDK ?= sky130A
export PDKPATH ?= $(PDK_ROOT)/$(PDK)


# PVT Corner Configuration (Temperature and Voltage)
# These can be changed to target different corners:
#   Temperature: -40C (m40C), 025C, 100C, 125C
#   Voltage: 1v60, 1v80, 1v95
#   Common corner combinations:
#     ff (fast-fast): 100C_1v95
#     tt (typical-typical): 025C_1v80
#     ss (slow-slow): 100C_1v60

# Design Configuration
TOP ?= MemoryAdapterMsgSync
RTL_DIR ?= ../output
CORNER ?= tt
TEMP ?= 025C
VOLT ?= 1v80

# Timing Configuration
DEFAULT_PERIOD ?= 10.0
CLOCK_UNCERTAINTY ?= 0.15
IO_DELAY_PERCENT ?= 20

# Directory Structure
SCRIPTS_DIR := scripts
CONSTRAINTS_DIR := constraints
REPORT_DIR := reports
NETLIST_DIR := netlist

# File Paths
SDC_FILE := $(CONSTRAINTS_DIR)/$(TOP).sdc
SYNTH_SCRIPT := $(SCRIPTS_DIR)/synth.ys
CONSTRAINT_GEN := $(SCRIPTS_DIR)/generate_constraints.py
REPORT_PARSER := $(SCRIPTS_DIR)/parse_reports.py

# Yosys Configuration
YOSYS ?= yosys
PYTHON ?= python3
STA ?= sta
VERILATOR ?= verilator

# Liberty file for timing analysis
LIBERTY_FILE := $(PDKPATH)/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__$(CORNER)_$(TEMP)_$(VOLT).lib

# Export variables for Yosys script
export TOP_MODULE := $(TOP)
export RTL_DIR := $(RTL_DIR)
export SDC_FILE := $(SDC_FILE)
export REPORT_DIR := $(REPORT_DIR)
export NETLIST_DIR := $(NETLIST_DIR)
export CORNER := $(CORNER)
export TEMP := $(TEMP)
export VOLT := $(VOLT)
export LIB_CORNER_TEMP_VOLT := $(LIBERTY_FILE)

# ============================================================================
# Phony Targets
# ============================================================================

.PHONY: all help clean constraints lint synth report check_env sta

# ============================================================================
# Main Targets
# ============================================================================

all: check_env lint constraints synth sta report
	@echo ""
	@echo "=========================================="
	@echo "  Synthesis Flow Complete!"
	@echo "=========================================="
	@echo "Module      : $(TOP)"
	@echo "Constraints : $(SDC_FILE)"
	@echo "Netlist     : $(NETLIST_DIR)/$(TOP)_synth.v"
	@echo "Reports     : $(REPORT_DIR)/"
	@echo "=========================================="

help:
	@echo "========================================================================"
	@echo "  Yosys Synthesis Flow for SKY130A PDK"
	@echo "========================================================================"
	@echo ""
	@echo "Targets:"
	@echo "  make all              - Run complete flow (constraints + synth + sta + report)"
	@echo "  make constraints      - Generate SDC timing constraints"
	@echo "  make synth            - Run Yosys synthesis"
	@echo "  make sta              - Run OpenSTA timing/power analysis"
	@echo "  make report           - Parse and display synthesis results"
	@echo "  make clean            - Remove generated files"
	@echo "  make check_env        - Verify environment and dependencies"
	@echo "  make help             - Show this help message"
	@echo ""
	@echo "Configuration Variables:"
	@echo "  TOP=<module>          - Top module name (default: $(TOP))"
	@echo "  RTL_DIR=<path>        - RTL directory (default: $(RTL_DIR))"
	@echo "  CORNER=<corner>       - PVT corner: ff,tt,ss (default: $(CORNER))"
	@echo "  DEFAULT_PERIOD=<ns>   - Clock period (default: $(DEFAULT_PERIOD)ns)"
	@echo "  CLOCK_UNCERTAINTY=<ns>- Clock uncertainty (default: $(CLOCK_UNCERTAINTY)ns)"
	@echo ""
	@echo "PDK Variables:"
	@echo "  PDK_ROOT=<path>       - PDK root path (default: $(PDK_ROOT))"
	@echo "  PDK=<name>            - PDK name (default: $(PDK))"
	@echo "  PDKPATH=<path>        - Full PDK path (default: $(PDKPATH))"
	@echo ""
	@echo "Examples:"
	@echo "  make all TOP=AsyncQueue"
	@echo "  make synth TOP=MemoryAdapterMsgSync CORNER=ff"
	@echo "  make constraints TOP=MyModule DEFAULT_PERIOD=20"
	@echo "  make sta TOP=MemoryAdapterMsgSync"
	@echo "  make report TOP=MemoryAdapterMsgSync"
	@echo ""
	@echo "========================================================================"

# ============================================================================
# Environment Check
# ============================================================================

check_env:
	@echo "Checking environment..."
	@echo "  TOP_MODULE    : $(TOP)"
	@echo "  RTL_DIR       : $(RTL_DIR)"
	@echo "  PDK_ROOT      : $(PDK_ROOT)"
	@echo "  PDK           : $(PDK)"
	@echo "  PDKPATH       : $(PDKPATH)"
	@echo "  CORNER        : $(CORNER)"
	@echo ""
	@if [ ! -d "$(RTL_DIR)" ]; then \
		echo "❌ Error: RTL directory not found: $(RTL_DIR)"; \
		exit 1; \
	fi
	@if [ ! -f "$(RTL_DIR)/$(TOP).sv" ]; then \
		echo "❌ Error: Top module file not found: $(RTL_DIR)/$(TOP).sv"; \
		exit 1; \
	fi
	@if [ ! -d "$(PDKPATH)" ]; then \
		echo "❌ Error: PDK path not found: $(PDKPATH)"; \
		echo "   Please check PDK_ROOT and PDK variables"; \
		exit 1; \
	fi
	@if ! command -v $(YOSYS) > /dev/null 2>&1; then \
		echo "❌ Error: Yosys not found in PATH"; \
		exit 1; \
	fi
	@if ! command -v $(PYTHON) > /dev/null 2>&1; then \
		echo "❌ Error: Python3 not found in PATH"; \
		exit 1; \
	fi
	@echo "✓ Environment check passed"

# ============================================================================
# Linting
# ============================================================================

lint: check_env
	@echo ""
	@echo "=========================================="
	@echo "  Running Verilator Lint"
	@echo "=========================================="
	@echo "  Checking all .sv files in $(RTL_DIR)"
	$(VERILATOR) --lint-only -Wall -Wno-fatal -I$(RTL_DIR) $(wildcard $(RTL_DIR)/*.sv)
	@echo ""
	@echo "✓ Lint complete"

# ============================================================================
# Constraint Generation
# ============================================================================

constraints: check_env $(SDC_FILE)

$(SDC_FILE): $(RTL_DIR)/$(TOP).sv $(CONSTRAINT_GEN)
	@echo ""
	@echo "=========================================="
	@echo "  Generating Timing Constraints"
	@echo "=========================================="
	@mkdir -p $(CONSTRAINTS_DIR)
	$(PYTHON) $(CONSTRAINT_GEN) \
		--top $(TOP) \
		--rtl-dir $(RTL_DIR) \
		--output $(SDC_FILE) \
		--period $(DEFAULT_PERIOD) \
		--uncertainty $(CLOCK_UNCERTAINTY) \
		--io-delay $(IO_DELAY_PERCENT)
	@echo ""

# ============================================================================
# Synthesis
# ============================================================================

synth: check_env constraints $(NETLIST_DIR)/$(TOP)_synth.v

$(NETLIST_DIR)/$(TOP)_synth.v: $(SYNTH_SCRIPT) $(SDC_FILE)
	@echo ""
	@echo "=========================================="
	@echo "  Running Yosys Synthesis"
	@echo "=========================================="
	@echo "  Module : $(TOP)"
	@echo "  Corner : $(CORNER)"
	@echo "  PDK    : $(PDKPATH)"
	@echo "=========================================="
	@mkdir -p $(REPORT_DIR) $(NETLIST_DIR)
	@# Create temporary script with substituted variables
	@sed -e 's|$$::env(RTL_DIR)|$(abspath $(RTL_DIR))|g' \
	     -e 's|$$::env(TOP_MODULE)|$(TOP)|g' \
	     -e 's|$$::env(REPORT_DIR)|$(abspath $(REPORT_DIR))|g' \
	     -e 's|$$::env(NETLIST_DIR)|$(abspath $(NETLIST_DIR))|g' \
	     -e 's|$$::env(PDKPATH)|$(PDKPATH)|g' \
	     -e 's|$$::env(CORNER)|$(CORNER)|g' \
	     -e 's|$$::env(TEMP)|$(TEMP)|g' \
	     -e 's|$$::env(VOLT)|$(VOLT)|g' \
	     -e 's|$$::env(LIB_CORNER_TEMP_VOLT)|$(LIBERTY_FILE)|g' \
	     -e 's|$$::env(SDC_FILE)|$(abspath $(SDC_FILE))|g' \
	     $(SCRIPTS_DIR)/synth.ys > $(REPORT_DIR)/synth_$(TOP).ys
	@# Run Yosys synthesis
	cd $(REPORT_DIR) && $(YOSYS) synth_$(TOP).ys | tee $(TOP)_yosys.log
	@rm -f $(REPORT_DIR)/synth_$(TOP).ys
	@echo ""
	@echo "✓ Synthesis complete"
	@echo "  Netlist : $(NETLIST_DIR)/$(TOP)_synth.v"
	@echo "  Log     : $(REPORT_DIR)/$(TOP)_yosys.log"

# ============================================================================
# Static Timing Analysis (STA)
# ============================================================================

sta: $(REPORT_DIR)/$(TOP)_sta_timing.rpt

$(REPORT_DIR)/$(TOP)_sta_timing.rpt: $(NETLIST_DIR)/$(TOP)_sta.v $(SDC_FILE)
	@echo ""
	@echo "=========================================="
	@echo "  Running OpenSTA Analysis"
	@echo "=========================================="
	@echo "  Module  : $(TOP)"
	@echo "  Corner  : $(CORNER)"
	@echo "  Liberty : $(LIBERTY_FILE)"
	@echo "=========================================="
	@if [ ! -f "$(LIBERTY_FILE)" ]; then \
		echo "❌ Error: Liberty file not found: $(LIBERTY_FILE)"; \
		exit 1; \
	fi
	@if ! command -v $(STA) > /dev/null 2>&1; then \
		echo "⚠️  Warning: OpenSTA not found. Skipping timing analysis."; \
		echo "  Install OpenSTA to get accurate timing and power estimates."; \
		touch $(REPORT_DIR)/$(TOP)_sta_timing.rpt; \
		touch $(REPORT_DIR)/$(TOP)_sta_power.rpt; \
	else \
		$(PYTHON) $(SCRIPTS_DIR)/run_sta.py \
			--netlist $(NETLIST_DIR)/$(TOP)_sta.v \
			--sdc $(SDC_FILE) \
			--liberty $(LIBERTY_FILE) \
			--top $(TOP) \
			--report-dir $(REPORT_DIR); \
		echo ""; \
		echo "✓ STA complete"; \
		echo "  Timing  : $(REPORT_DIR)/$(TOP)_sta_timing.rpt"; \
		echo "  Power   : $(REPORT_DIR)/$(TOP)_sta_power.rpt"; \
	fi

# ============================================================================
# Report Generation
# ============================================================================

report: $(REPORT_DIR)/$(TOP)_stats.txt
	@echo ""
	@echo "=========================================="
	@echo "  Synthesis Report"
	@echo "=========================================="
	@$(PYTHON) $(REPORT_PARSER) --top $(TOP) --report-dir $(REPORT_DIR) --detailed

$(REPORT_DIR)/$(TOP)_stats.txt:
	@echo "❌ Error: Statistics file not found. Run 'make synth' first."
	@exit 1

# ============================================================================
# Utility Targets
# ============================================================================

clean:
	@echo "Cleaning generated files..."
	rm -rf $(CONSTRAINTS_DIR)/*.sdc
	rm -rf $(REPORT_DIR)/*
	rm -rf $(NETLIST_DIR)/*
	@echo "✓ Clean complete"

# Quick report (without detailed breakdown)
quick-report: $(REPORT_DIR)/$(TOP)_stats.txt
	@$(PYTHON) $(REPORT_PARSER) --top $(TOP) --report-dir $(REPORT_DIR)

# Show Yosys log
show-log:
	@if [ -f "$(REPORT_DIR)/$(TOP)_yosys.log" ]; then \
		less $(REPORT_DIR)/$(TOP)_yosys.log; \
	else \
		echo "❌ Log file not found. Run 'make synth' first."; \
	fi

# Validate scripts
validate:
	@echo "Validating synthesis scripts..."
	@$(PYTHON) -m py_compile $(CONSTRAINT_GEN)
	@$(PYTHON) -m py_compile $(REPORT_PARSER)
	@echo "✓ Python scripts validated"

# ============================================================================
# Debug Targets
# ============================================================================

debug-env:
	@echo "Environment Variables:"
	@echo "  PDK_ROOT           = $(PDK_ROOT)"
	@echo "  PDK                = $(PDK)"
	@echo "  PDKPATH            = $(PDKPATH)"
	@echo "  TOP                = $(TOP)"
	@echo "  TOP_MODULE         = $(TOP_MODULE)"
	@echo "  RTL_DIR            = $(RTL_DIR)"
	@echo "  CORNER             = $(CORNER)"
	@echo "  DEFAULT_PERIOD     = $(DEFAULT_PERIOD)"
	@echo "  CLOCK_UNCERTAINTY  = $(CLOCK_UNCERTAINTY)"
	@echo "  SDC_FILE           = $(SDC_FILE)"
	@echo "  YOSYS              = $(YOSYS)"
	@echo "  PYTHON             = $(PYTHON)"
