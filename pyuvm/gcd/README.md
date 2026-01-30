# GCD Verification Environment

This directory contains a complete pyUVM-based verification environment for the GCD (Greatest Common Divisor) module.

## Overview

The GCD module computes the greatest common divisor of two 16-bit unsigned integers using the subtraction method.

### Module Interface

- **Inputs:**
  - `clock`: Clock signal
  - `reset`: Active-high reset
  - `io_value1[15:0]`: First input value
  - `io_value2[15:0]`: Second input value
  - `io_loadingValues`: Load signal to start new computation

- **Outputs:**
  - `io_outputGCD[15:0]`: Computed GCD result
  - `io_outputValid`: Result valid flag (asserted when computation complete)

## Verification Environment

The verification setup uses **pyUVM** (Python UVM) with **cocotb** for RTL simulation.

### Components

- **gcd_transaction.py** - Transaction class with randomization
- **gcd_driver.py** - Drives stimuli to the DUT
- **gcd_monitor.py** - Monitors DUT interface
- **gcd_scoreboard.py** - Verifies correctness using Python's `math.gcd()`
- **gcd_coverage.py** - Functional coverage collector
- **gcd_sequences.py** - Test sequences (random, directed, corner cases)
- **gcd_agent.py** - Groups driver and monitor
- **gcd_env.py** - Top-level environment
- **gcd_test.py** - Test definitions and cocotb integration

## Quick Start

### 1. Install Dependencies

```bash
cd /home/binhkieudo/Workspace/uvm/chisel7-template
pip install -r verification/requirements.txt
```

### 2. Generate Verilog (if not already done)

```bash
sbt "runMain gcd.GCD"
```

This creates `GCD.sv` in the project root.

### 3. Run Tests

```bash
cd verification/gcd
make
```

This runs all test scenarios defined in `gcd_test.py`:

- `gcd_random_test` - Random stimulus
- `gcd_directed_test` - Known test cases
- `gcd_corner_case_test` - Edge cases
- `gcd_full_test` - Comprehensive test suite

### 4. View Waveforms

Waveforms are generated in FST format (for better performance):

```bash
gtkwave dump.fst
```

## Test Scenarios

### Random Test

- Generates 100 random transaction pairs
- Includes corner cases (values of 1, equal values, etc.)

### Directed Test

Specific test cases:

- Both values zero: `(0, 0)`
- One value zero: `(0, 100)`, `(100, 0)`
- Prime numbers (coprime): `(17, 19)`
- Known GCD values: `(48, 18)` → GCD=6
- Equal values: `(100, 100)`, `(65535, 65535)`
- Powers of 2: `(256, 1024)`

### Corner Case Test

- Maximum value cases: `(65535, 1)`, `(65535, 65534)`
- Boundary values: `(255, 256)`
- Small primes: `(3, 5)`, `(7, 11)`, `(13, 17)`

### Back-to-Back Test

- Stress test with 30 consecutive transactions
- Mix of quick (small values) and slow (large values) computations

## Coverage Goals

The functional coverage collector tracks:

- **Zero cases**: One or both values are 0
- **One cases**: One value is 1
- **Equal values**: Both inputs are the same
- **Coprime cases**: GCD result is 1
- **Maximum value cases**: Contains 16-bit max value (65535)
- **Power of 2 cases**: Inputs are powers of 2

## Expected Results

- All transactions should pass verification
- Scoreboard compares DUT output against Python's `math.gcd()`
- Coverage report shows distribution of test scenarios
- No timeouts or protocol violations

## Troubleshooting

### Import Errors

Make sure you're in the `verification/gcd` directory when running tests, or ensure Python can find the modules.

### Simulation Errors

- Verify `GCD.sv` exists in the project root
- Check that verilator is installed: `verilator --version`
- Review `sim_build/` directory for compilation logs

### Test Failures

- Check scoreboard output for mismatches
- View waveforms to debug protocol issues
- Increase logging verbosity in `gcd_test.py`

## File Structure

```
verification/
├── requirements.txt       # Python dependencies
└── gcd/
    ├── Makefile           # Cocotb simulation setup
    ├── README.md          # This file
    ├── gcd_transaction.py # Transaction definition
    ├── gcd_driver.py      # Stimulus driver
    ├── gcd_monitor.py     # Interface monitor
    ├── gcd_scoreboard.py  # Checker
    ├── gcd_coverage.py    # Coverage collector
    ├── gcd_sequences.py   # Test sequences
    ├── gcd_agent.py       # Agent (driver + monitor)
    ├── gcd_env.py         # UVM environment
    └── gcd_test.py        # Cocotb tests
```

## Extending the Tests

To add new test scenarios:

1. Create a new sequence in `gcd_sequences.py`
2. Create a new test class in `gcd_test.py` extending `GCDTestBase`
3. Add a `@cocotb.test()` function to run it
4. Run `make` to execute

## Notes

- The GCD algorithm is iterative (subtraction-based), so computation time varies with input values
- Larger values and values with small GCD require more clock cycles
- The driver includes timeout protection (1000 cycles max per transaction)
- Signal names in the generated SystemVerilog use `io_` prefix (Chisel convention)
