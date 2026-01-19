# Yosys Synthesis Flow for SKY130A PDK

A comprehensive synthesis flow using Yosys with the SkyWater SKY130A PDK. This flow includes automatic constraint generation, technology mapping, resource estimation, and detailed reporting.

## Overview

This synthesis flow provides:

- **Automated Constraint Generation**: Analyzes RTL to detect clocks and generate SDC timing constraints
- **SKY130A Technology Mapping**: Maps designs to SkyWater SKY130 standard cells
- **Comprehensive Reporting**: Logic elements, flip-flops, area, and power estimates
- **Multiple Output Formats**: Verilog, JSON, and BLIF netlists
- **Easy Automation**: Makefile-based workflow with configurable parameters

## Directory Structure

```
syn/
├── scripts/
│   ├── generate_constraints.py   # Auto-generate SDC from RTL
│   ├── synth.ys                  # Yosys synthesis script
│   └── parse_reports.py          # Report parser and pretty-printer
├── constraints/                  # Generated SDC files
├── reports/                      # Synthesis reports and logs
├── netlist/                      # Synthesized netlists
├── Makefile                      # Build automation
└── README.md                     # This file
```

## Prerequisites

### Required Tools

1. **Yosys** - Open-source synthesis tool
   ```bash
   # Check installation
   yosys -V
   ```

2. **Python 3** - For constraint generation and report parsing
   ```bash
   python3 --version
   ```

3. **SKY130A PDK** - SkyWater 130nm Process Design Kit
   - Default location: `/opt/pdk/sky130A`
   - Can be overridden with `PDK_ROOT` and `PDK` variables

### PDK Setup

Ensure the PDK is properly installed with liberty files:
```bash
ls $PDK_ROOT/$PDK/libs.ref/sky130_fd_sc_hd/lib/
# Should show: sky130_fd_sc_hd__ff_*.lib, sky130_fd_sc_hd__tt_*.lib, etc.
```

## Quick Start

### 1. Run Complete Flow

Synthesize the default module (`MemoryAdapterMsgSync`):

```bash
cd syn
make all
```

This will:
1. Generate timing constraints
2. Run synthesis
3. Display formatted results

### 2. Synthesize a Different Module

```bash
make all TOP=AsyncQueue
```

### 3. View Help

```bash
make help
```

## Usage

### Makefile Targets

| Target | Description |
|--------|-------------|
| `make all` | Run complete flow (constraints → synthesis → report) |
| `make constraints` | Generate SDC timing constraints only |
| `make synth` | Run Yosys synthesis |
| `make report` | Parse and display synthesis results |
| `make clean` | Remove generated files |
| `make check_env` | Verify environment and dependencies |
| `make help` | Display usage information |

### Configuration Variables

Control the synthesis flow with these variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TOP` | Top module name | `MemoryAdapterMsgSync` |
| `RTL_DIR` | RTL source directory | `../output` |
| `CORNER` | PVT corner (ff/tt/ss) | `tt` |
| `DEFAULT_PERIOD` | Clock period (ns) | `10.0` (100 MHz) |
| `CLOCK_UNCERTAINTY` | Clock uncertainty (ns) | `0.2` |
| `PDK_ROOT` | PDK root directory | `/opt/pdk` |
| `PDK` | PDK name | `sky130A` |

### Examples

#### Example 1: Synthesize with Fast Corner

```bash
make all TOP=MemoryAdapterMsgSync CORNER=ff
```

#### Example 2: Target 50 MHz (20ns period)

```bash
make all TOP=AsyncQueue DEFAULT_PERIOD=20
```

#### Example 3: Generate Constraints Only

```bash
make constraints TOP=MyModule DEFAULT_PERIOD=15
```

#### Example 4: Re-run Report

```bash
make report TOP=MemoryAdapterMsgSync
```

## Constraint Generation

The `generate_constraints.py` script automatically analyzes your RTL to:

1. **Detect Clocks**: Identifies clock signals based on naming patterns (e.g., `*Clock`, `*clk`)
2. **Identify Async Domains**: Finds asynchronous clock domain crossings
3. **Generate I/O Constraints**: Creates input/output delay constraints
4. **Set False Paths**: Marks async paths between clock domains

### Clock Detection

The script automatically detects clocks from module ports:

```systemverilog
module MemoryAdapterMsgSync(
  input io_blockClock,    // ← Detected as clock
  input io_hubClock,      // ← Detected as clock
  input io_blockReset,
  // ...
);
```

### Generated SDC Format

Example generated constraints:

```sdc
# Clock Definitions
create_clock -name io_blockClock -period 10.0 [get_ports io_blockClock]
create_clock -name io_hubClock -period 10.0 [get_ports io_hubClock]

# Clock Uncertainty
set_clock_uncertainty 0.2 [all_clocks]

# Asynchronous Clock Domain Crossings
set_false_path -from [get_clocks io_blockClock] -to [get_clocks io_hubClock]
set_false_path -from [get_clocks io_hubClock] -to [get_clocks io_blockClock]

# Input Delays (30% of clock period = 3.0 ns)
set_input_delay -clock io_blockClock 3.0 [get_ports io_msgIn]
set_input_delay -clock io_blockClock 3.0 [get_ports io_msgInValid]
# ...
```

### Manual Constraint Editing

The generated SDC file can be manually edited:

```bash
vim constraints/MemoryAdapterMsgSync.sdc
```

After editing, re-run synthesis:

```bash
make synth
```

## Synthesis Flow Details

### Process Overview

1. **RTL Elaboration**
   - Reads SystemVerilog files from `filelist.f`
   - Parses module hierarchy
   - Checks for syntax errors

2. **High-Level Synthesis**
   - Processes `always` blocks → sequential logic
   - FSM extraction and optimization
   - Memory inference
   - Multi-level optimization

3. **Technology Mapping**
   - Maps to SKY130A standard cells
   - Uses `sky130_fd_sc_hd` library (high-density)
   - Applies liberty file for target corner

4. **Statistics Collection**
   - Cell counts by type
   - Area estimation
   - Resource utilization

5. **Netlist Generation**
   - Verilog netlist (`.v`)
   - JSON netlist (`.json`)
   - BLIF netlist (`.blif`)

### PVT Corners

The flow supports different Process-Voltage-Temperature corners:

| Corner | Description | Liberty File |
|--------|-------------|--------------|
| `ff` | Fast-Fast (best case) | `sky130_fd_sc_hd__ff_100C_1v95.lib` |
| `tt` | Typical-Typical (nominal) | `sky130_fd_sc_hd__tt_025C_1v80.lib` |
| `ss` | Slow-Slow (worst case) | `sky130_fd_sc_hd__ss_100C_1v60.lib` |

## Report Parsing

The `parse_reports.py` script extracts and displays:

### Metrics Displayed

- **Logic Elements**: Combinational logic gates (AND, OR, XOR, MUX, etc.)
- **Flip-Flops**: Total sequential elements
- **Reset FFs**: Flip-flops with asynchronous reset/set
- **Latches**: Latch count (warning if > 0)
- **Est. Max Frequency**: Rough frequency estimate
- **Est. Power**: Dynamic power estimate at 100 MHz
- **Total Area**: Cell area in µm²

### Example Output

```
╔══════════════════════════════════════════════════╗
║        Synthesis Results Summary                 ║
║            Module: MemoryAdapterMsgSync          ║
╠══════════════════════════════════════════════════╣
║ Logic Elements     :                        1,234 ║
║ Flip-Flops (Total) :                          567 ║
║ Reset FFs          :                          543 ║
║ Latches            :                            0 ║
╠══════════════════════════════════════════════════╣
║ Est. Max Frequency :                  150.0 MHz ║
║ Est. Power @ 100MHz:                    12.34 mW ║
║ Total Area         :                 45678.9 µm² ║
╚══════════════════════════════════════════════════╝
```

### Detailed Cell Breakdown

Use the `--detailed` flag for cell-by-cell breakdown:

```bash
python3 scripts/parse_reports.py --top MemoryAdapterMsgSync --report-dir reports --detailed
```

## Output Files

### Constraints Directory

- `<module>.sdc` - SDC timing constraints

### Reports Directory

- `<module>_stats.txt` - Detailed statistics (human-readable)
- `<module>_stats.json` - Statistics in JSON format
- `<module>_cells.txt` - Cell usage report
- `<module>_pre_synth_stats.txt` - Pre-synthesis statistics
- `<module>_yosys.log` - Complete Yosys log

### Netlist Directory

- `<module>_synth.v` - Synthesized Verilog netlist
- `<module>_synth.json` - JSON netlist
- `<module>_synth.blif` - BLIF netlist

## Troubleshooting

### Issue: "PDK path not found"

**Solution**: Verify PDK installation and set environment variables:

```bash
export PDK_ROOT=/opt/pdk
export PDK=sky130A
export PDKPATH=$PDK_ROOT/$PDK
make check_env
```

### Issue: "Yosys not found"

**Solution**: Install Yosys or add to PATH:

```bash
# Ubuntu/Debian
sudo apt install yosys

# Or build from source
git clone https://github.com/YosysHQ/yosys.git
cd yosys
make
sudo make install
```

### Issue: "Top module file not found"

**Solution**: Ensure RTL files are in the correct directory:

```bash
ls ../output/MemoryAdapterMsgSync.sv
# Or specify custom RTL directory
make all TOP=MyModule RTL_DIR=/path/to/rtl
```

### Issue: Liberty file errors

**Solution**: Verify PDK library files exist:

```bash
ls $PDKPATH/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
```

### Issue: Synthesis errors

**Solution**: Check Yosys log for details:

```bash
make show-log
# Or directly:
less reports/MemoryAdapterMsgSync_yosys.log
```

### Advanced Usage

### Running Yosys Script Directly

The synthesis script can be run directly without the Makefile:

```bash
cd syn/scripts
export TOP_MODULE=MemoryAdapterMsgSync
export RTL_DIR=../../output
export REPORT_DIR=../reports
export NETLIST_DIR=../netlist
export PDKPATH=/opt/pdk/sky130A
export CORNER=tt
yosys synth.ys
```

The script uses TCL to set defaults if environment variables are not provided.

### Custom Yosys Commands

Edit `scripts/synth.ys` to add custom optimization passes or commands.

### Integration with OpenSTA

For detailed timing analysis, use OpenSTA with the generated SDC:

```bash
sta
read_liberty $PDKPATH/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog netlist/MemoryAdapterMsgSync_synth.v
link_design MemoryAdapterMsgSync
read_sdc constraints/MemoryAdapterMsgSync.sdc
report_checks
```

### Batch Processing

Synthesize multiple modules:

```bash
for module in AsyncQueue MemoryAdapterMsgSync CdcMem; do
    make all TOP=$module
done
```

## Recommendations

1. **Always review generated constraints** before synthesis
2. **Use appropriate PVT corner** for your target application
3. **Validate timing** with OpenSTA or commercial tools
4. **Check for latches** (usually indicate design issues)
5. **Iterate on clock periods** to meet timing goals

## References

- [Yosys Documentation](https://yosyshq.net/yosys/)
- [SkyWater SKY130 PDK](https://github.com/google/skywater-pdk)
- [SDC Format Specification](https://www.synopsys.com/community/interoperability-programs/tap-in.html)

## License

This synthesis flow is provided as-is for use with the Chisel7 template project.
