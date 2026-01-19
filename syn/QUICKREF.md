# Yosys Synthesis Flow - Quick Reference

## Quick Start

```bash
cd syn
make all                    # Run complete flow with default settings
make all TOP=AsyncQueue     # Synthesize different module
```

## Common Commands

### Generate Constraints Only
```bash
make constraints TOP=MemoryAdapterMsgSync
```

### Run Synthesis
```bash
make synth TOP=MemoryAdapterMsgSync
```

### View Report
```bash
make report TOP=MemoryAdapterMsgSync
```

### Clean Generated Files
```bash
make clean
```

### Verify Environment
```bash
make check_env
```

## Configuration

### Set Clock Frequency
```bash
# 50 MHz (20ns period)
make all DEFAULT_PERIOD=20

# 200 MHz (5ns period)
make all DEFAULT_PERIOD=5
```

### Select PVT Corner
```bash
make all CORNER=ff    # Fast-Fast (best case)
make all CORNER=tt    # Typical-Typical (default)
make all CORNER=ss    # Slow-Slow (worst case)
```

### Custom PDK Path
```bash
make all PDK_ROOT=/custom/path/pdk PDK=sky130A
```

## File Locations

| Item | Location |
|------|----------|
| SDC Constraints | `constraints/<module>.sdc` |
| Synthesized Netlist | `netlist/<module>_synth.v` |
| Reports | `reports/<module>_*.txt` |
| Yosys Log | `reports/<module>_yosys.log` |

## Script Standalone Usage

### Run Yosys Script Directly

```bash
cd syn/scripts
export TOP_MODULE=MemoryAdapterMsgSync
export RTL_DIR=../../output
export PDKPATH=/opt/pdk/sky130A
yosys synth.ys
```

Variables have defaults if not set: TOP_MODULE=MemoryAdapterMsgSync, RTL_DIR=../output, CORNER=tt

### Generate Constraints Manually
```bash
python3 scripts/generate_constraints.py \
  --top MemoryAdapterMsgSync \
  --rtl-dir ../output \
  --period 10 \
  --uncertainty 0.2
```

### Parse Reports Manually
```bash
python3 scripts/parse_reports.py \
  --top MemoryAdapterMsgSync \
  --report-dir reports \
  --detailed
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PDK_ROOT` | `/opt/pdk` | PDK root directory |
| `PDK` | `sky130A` | PDK name |
| `TOP` | `MemoryAdapterMsgSync` | Top module |
| `RTL_DIR` | `../output` | RTL source directory |
| `CORNER` | `tt` | PVT corner (ff/tt/ss) |
| `DEFAULT_PERIOD` | `10.0` | Clock period (ns) |
| `CLOCK_UNCERTAINTY` | `0.2` | Clock uncertainty (ns) |

## Troubleshooting

### Issue: PDK not found
```bash
export PDK_ROOT=/opt/pdk
export PDK=sky130A
export PDKPATH=$PDK_ROOT/$PDK
make check_env
```

### Issue: Module file not found
```bash
# Check RTL files exist
ls ../output/MemoryAdapterMsgSync.sv

# Or specify custom path
make all RTL_DIR=/path/to/rtl
```

### View Yosys Log for Errors
```bash
less reports/MemoryAdapterMsgSync_yosys.log
# or
make show-log
```

## Examples

### Example 1: Synthesize AsyncQueue at 100 MHz
```bash
make all TOP=AsyncQueue DEFAULT_PERIOD=10
```

### Example 2: Fast Corner, 200 MHz
```bash
make all TOP=MemoryAdapterMsgSync CORNER=ff DEFAULT_PERIOD=5
```

### Example 3: Constraints with Custom I/O Delay
```bash
python3 scripts/generate_constraints.py \
  -t MemoryAdapterMsgSync \
  -r ../output \
  --period 8 \
  --io-delay 40
```

### Example 4: Detailed Report
```bash
python3 scripts/parse_reports.py \
  -t MemoryAdapterMsgSync \
  -r reports \
  --detailed
```

## Integration with OpenSTA

After synthesis, use OpenSTA for detailed timing analysis:

```bash
sta
read_liberty $PDKPATH/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog netlist/MemoryAdapterMsgSync_synth.v
link_design MemoryAdapterMsgSync
read_sdc constraints/MemoryAdapterMsgSync.sdc
report_checks -path_delay min_max
report_checks -path_delay max
report_tns
report_wns
```

## ABC Synthesis Optimization Script

In `synth.ys`, the `abc` command uses a specialized script for high-performance synthesis:

```bash
-script +strash;ifraig;dch,-f;map;buffer;upsize;dnsize;stime,-p
```

| Command | Action | Description |
|:---|:---|:---|
| `strash` | Structural Hash | Converts design to AIG and performs basic structural cleanup. |
| `ifraig` | Functional AIG | Merges functionally equivalent nodes to reduce logic. |
| `dch` | Choice Hashing | Creates multiple functionally equivalent versions of logic for mapping. |
| `map` | Tech Mapping | Maps abstract logic to Sky130 standard cells based on SDC. |
| `buffer` | Buffering | Inserts buffer trees to fix Max Fanout and Max Capacitance. |
| `upsize` / `dnsize` | Sizing | Adjusts cell drive strength to optimize timing vs area. |
| `stime -p` | Timing Report | Performs internal timing analysis and prints results to log. |

---

## Tips

1. **Always review generated constraints** before synthesis
2. **Run multiple corners** to understand timing margins
3. **Use OpenSTA** for accurate timing analysis
4. **Check for latches** in the report (usually indicates issues)
5. **Iterate on clock period** to find maximum frequency

## Help

```bash
make help                                    # Makefile help
python3 scripts/generate_constraints.py -h   # Constraint gen help
python3 scripts/parse_reports.py -h          # Parser help
```

For full documentation, see [README.md](README.md)
