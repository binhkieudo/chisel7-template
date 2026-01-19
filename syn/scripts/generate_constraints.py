#!/usr/bin/env python3
"""
Constraint Generation Script for Yosys Synthesis
Automatically analyzes RTL files and generates SDC (Synopsys Design Constraints)
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple


class RTLAnalyzer:
    """Analyzes RTL files to extract timing-related information"""
    
    def __init__(self, rtl_dir: Path, top_module: str):
        self.rtl_dir = rtl_dir
        self.top_module = top_module
        self.clocks: Set[str] = set()
        self.clock_pairs: List[Tuple[str, str]] = []
        self.inputs: Set[str] = set()
        self.outputs: Set[str] = set()
        
    def parse_module(self, filepath: Path):
        """Parse a SystemVerilog file to extract module ports"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Find the top module definition
        module_pattern = rf'module\s+{re.escape(self.top_module)}\s*\((.*?)\);'
        match = re.search(module_pattern, content, re.DOTALL)
        
        if not match:
            return False
            
        ports_section = match.group(1)
        
        # Clean up the ports section for easier parsing
        # Remove comments and extra whitespace
        ports_section = re.sub(r'//.*', '', ports_section)
        ports_section = re.sub(r'/\*.*?\*/', '', ports_section, flags=re.DOTALL)
        
        # Parse port declarations
        # In SystemVerilog, multiple ports can share a direction/type:
        #   input clk, rst,
        #   input [7:0] data
        # Or with continuation:
        #   input io_blockClock,
        #         io_hubClock,
        
        current_direction = None
        
        # Split by commas and process each port
        for line in ports_section.split(','):
            line = line.strip()
            if not line:
                continue
            
            # Check if this line has a direction keyword
            direction_match = re.match(r'(input|output|inout)\s+', line)
            if direction_match:
                current_direction = direction_match.group(1)
                # Remove direction and parse rest
                line = line[direction_match.end():]
            
            # Extract port name (after optional width spec)
            # Pattern: optional [width] followed by port_name
            port_match = re.search(r'(?:\[[\d:]+\])?\s*(\w+)', line)
            if port_match and current_direction:
                port_name = port_match.group(1)
                
                # Detect clock signals (common naming patterns)
                if self._is_clock_signal(port_name):
                    self.clocks.add(port_name)
                
                if current_direction == 'input':
                    self.inputs.add(port_name)
                elif current_direction == 'output':
                    self.outputs.add(port_name)
        
        # Detect async clock domain crossings
        self._detect_async_clocks()
        
        return True
    
    def _is_clock_signal(self, signal_name: str) -> bool:
        """Determine if a signal is a clock based on naming conventions"""
        clock_patterns = [
            r'.*[Cc]lock.*',
            r'.*[Cc]lk.*',
            r'.*_ck$',
            r'clk_.*'
        ]
        return any(re.match(pattern, signal_name) for pattern in clock_patterns)
    
    def _detect_async_clocks(self):
        """Detect asynchronous clock domain pairs"""
        clock_list = sorted(self.clocks)
        
        # Heuristic: Different clock domains are typically asynchronous
        # Look for patterns like io_blockClock vs io_hubClock, io_enqClock vs io_deqClock
        for i, clk1 in enumerate(clock_list):
            for clk2 in clock_list[i+1:]:
                # Check if clocks have different base names
                base1 = self._get_clock_base(clk1)
                base2 = self._get_clock_base(clk2)
                
                if base1 != base2:
                    self.clock_pairs.append((clk1, clk2))
    
    def _get_clock_base(self, clock_name: str) -> str:
        """Extract base clock name (remove prefixes like io_, suffixes like Clock)"""
        # Remove common prefixes
        name = re.sub(r'^(io_|i_|o_)', '', clock_name)
        # Remove Clock/clock suffix
        name = re.sub(r'(Clock|clock|Clk|clk)$', '', name)
        return name


class SDCGenerator:
    """Generates SDC constraint files"""
    
    def __init__(self, analyzer: RTLAnalyzer, default_period: float, 
                 clock_uncertainty: float, io_delay_percent: float,
                 load_cap: float, drive_cell: str, drive_pin: str, transition: float):
        self.analyzer = analyzer
        self.default_period = default_period
        self.clock_uncertainty = clock_uncertainty
        self.io_delay_percent = io_delay_percent
        self.load_cap = load_cap
        self.drive_cell = drive_cell
        self.drive_pin = drive_pin
        self.transition = transition
        
    def generate(self, output_file: Path):
        """Generate complete SDC file"""
        lines = []
        
        # Header
        lines.append("# Auto-generated SDC constraints")
        lines.append(f"# Top module: {self.analyzer.top_module}")
        lines.append(f"# Generated by: generate_constraints.py")
        lines.append("")
        
        # Clock definitions
        lines.append("# Clock Definitions")
        lines.append(f"# Default period: {self.default_period} ns ({1000/self.default_period:.1f} MHz)")
        lines.append("")
        
        for clock in sorted(self.analyzer.clocks):
            lines.append(f"create_clock -name {clock} -period {self.default_period} [get_ports {clock}]")
        
        lines.append("")
        
        # Clock uncertainty
        if self.analyzer.clocks:
            lines.append("# Clock Uncertainty (jitter + skew)")
            lines.append(f"set_clock_uncertainty {self.clock_uncertainty} [all_clocks]")
            lines.append("")
        
        # Async clock domain crossings
        if self.analyzer.clock_pairs:
            lines.append("# Asynchronous Clock Domain Crossings")
            lines.append("# These clock domains are assumed to be asynchronous")
            for clk1, clk2 in self.analyzer.clock_pairs:
                lines.append(f"set_false_path -from [get_clocks {clk1}] -to [get_clocks {clk2}]")
                lines.append(f"set_false_path -from [get_clocks {clk2}] -to [get_clocks {clk1}]")
            lines.append("")
        
        # I/O delays
        io_delay = self.default_period * self.io_delay_percent / 100.0
        
        # Input delays (non-clock inputs)
        input_ports = self.analyzer.inputs - self.analyzer.clocks
        if input_ports:
            lines.append("# Input Delays")
            lines.append(f"# Set to {self.io_delay_percent}% of clock period = {io_delay:.2f} ns")
            
            # Group inputs by likely clock domain (heuristic based on naming)
            for clock in sorted(self.analyzer.clocks):
                related_inputs = self._find_related_ports(input_ports, clock)
                if related_inputs:
                    lines.append(f"# Inputs related to {clock}")
                    for port in sorted(related_inputs):
                        lines.append(f"set_input_delay -clock {clock} {io_delay} [get_ports {port}]")
            
            # Remaining inputs - assign to first clock
            if self.analyzer.clocks:
                first_clock = sorted(self.analyzer.clocks)[0]
                remaining = input_ports - set().union(*[
                    self._find_related_ports(input_ports, clk) 
                    for clk in self.analyzer.clocks
                ])
                if remaining:
                    lines.append(f"# Other inputs (default to {first_clock})")
                    for port in sorted(remaining):
                        lines.append(f"set_input_delay -clock {first_clock} {io_delay} [get_ports {port}]")
            
            lines.append("")
        
        # Output delays (non-clock outputs)
        output_ports = self.analyzer.outputs - self.analyzer.clocks
        if output_ports:
            lines.append("# Output Delays")
            lines.append(f"# Set to {self.io_delay_percent}% of clock period = {io_delay:.2f} ns")
            
            for clock in sorted(self.analyzer.clocks):
                related_outputs = self._find_related_ports(output_ports, clock)
                if related_outputs:
                    lines.append(f"# Outputs related to {clock}")
                    for port in sorted(related_outputs):
                        lines.append(f"set_output_delay -clock {clock} {io_delay} [get_ports {port}]")
            
            # Remaining outputs
            if self.analyzer.clocks:
                first_clock = sorted(self.analyzer.clocks)[0]
                remaining = output_ports - set().union(*[
                    self._find_related_ports(output_ports, clk) 
                    for clk in self.analyzer.clocks
                ])
                if remaining:
                    lines.append(f"# Other outputs (default to {first_clock})")
                    for port in sorted(remaining):
                        lines.append(f"set_output_delay -clock {first_clock} {io_delay} [get_ports {port}]")
            
            lines.append("")
        
        # Environmental Constraints
        lines.append("# Environmental Constraints")
        lines.append(f"# Output Load: {self.load_cap} pF")
        lines.append(f"set_load {self.load_cap} [all_outputs]")
        
        lines.append(f"# Input Driving Cell: {self.drive_cell} (pin {self.drive_pin})")
        lines.append(f"set_driving_cell -lib_cell {self.drive_cell} -pin {self.drive_pin} [all_inputs]")
        
        if self.analyzer.clocks:
            lines.append(f"# Clock Transition: {self.transition} ns")
            lines.append(f"set_clock_transition {self.transition} [all_clocks]")
        
        lines.append("")

        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ Generated SDC constraints: {output_file}")
        self._print_summary()
    
    def _find_related_ports(self, ports: Set[str], clock: str) -> Set[str]:
        """Find ports likely related to a specific clock domain"""
        # Extract clock domain identifier from clock name
        # e.g., io_blockClock -> block, io_hubClock -> hub
        clock_domain = re.sub(r'^(io_|i_|o_)', '', clock)
        clock_domain = re.sub(r'(Clock|clock|Clk|clk)$', '', clock_domain)
        
        related = set()
        for port in ports:
            # Check if port name contains the clock domain identifier
            if clock_domain.lower() in port.lower():
                related.add(port)
        
        return related
    
    def _print_summary(self):
        """Print a summary of generated constraints"""
        print("\n" + "="*60)
        print("Constraint Generation Summary")
        print("="*60)
        print(f"Top Module      : {self.analyzer.top_module}")
        print(f"Clocks Found    : {len(self.analyzer.clocks)}")
        for clock in sorted(self.analyzer.clocks):
            print(f"  - {clock}")
        print(f"Async Pairs     : {len(self.analyzer.clock_pairs)}")
        print(f"Input Ports     : {len(self.analyzer.inputs - self.analyzer.clocks)}")
        print(f"Output Ports    : {len(self.analyzer.outputs - self.analyzer.clocks)}")
        print(f"Clock Period    : {self.default_period} ns ({1000/self.default_period:.1f} MHz)")
        print(f"Clock Uncertainty: {self.clock_uncertainty} ns")
        print(f"I/O Delay       : {self.io_delay_percent}% of period = {self.default_period * self.io_delay_percent / 100:.2f} ns")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Generate SDC timing constraints from RTL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate constraints for MemoryAdapterMsgSync
  %(prog)s -t MemoryAdapterMsgSync -r ../output -o constraints/MemoryAdapterMsgSync.sdc
  
  # Use custom clock period (50 MHz = 20ns)
  %(prog)s -t MyModule -r ../output -p 20
  
  # Specify clock uncertainty
  %(prog)s -t MyModule -r ../output -u 0.5
        '''
    )
    
    parser.add_argument('-t', '--top', required=True,
                        help='Top module name')
    parser.add_argument('-r', '--rtl-dir', default='../output',
                        help='RTL directory (default: ../output)')
    parser.add_argument('-o', '--output',
                        help='Output SDC file (default: constraints/<top>.sdc)')
    parser.add_argument('-p', '--period', type=float,
                        default=float(os.getenv('DEFAULT_PERIOD', '10.0')),
                        help='Default clock period in ns (default: 10.0 = 100MHz)')
    parser.add_argument('-u', '--uncertainty', type=float,
                        default=float(os.getenv('CLOCK_UNCERTAINTY', '0.2')),
                        help='Clock uncertainty in ns (default: 0.2)')
    parser.add_argument('--io-delay', type=float, default=30.0,
                        help='I/O delay as %% of clock period (default: 30)')
    parser.add_argument('--load', type=float, default=0.03,
                        help='Output load capacitance in pF (default: 0.03)')
    parser.add_argument('--drive-cell', default='sky130_fd_sc_hd__buf_2',
                        help='Input driving cell (default: sky130_fd_sc_hd__buf_2)')
    parser.add_argument('--drive-pin', default='A',
                        help='Input driving cell pin (default: A)')
    parser.add_argument('--transition', type=float, default=0.15,
                        help='Clock transition time in ns (default: 0.15)')
    
    args = parser.parse_args()
    
    # Setup paths
    rtl_dir = Path(args.rtl_dir)
    if not rtl_dir.exists():
        print(f"Error: RTL directory not found: {rtl_dir}", file=sys.stderr)
        return 1
    
    # Find top module file
    top_file = rtl_dir / f"{args.top}.sv"
    if not top_file.exists():
        print(f"Error: Top module file not found: {top_file}", file=sys.stderr)
        return 1
    
    # Default output path
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = Path('constraints') / f"{args.top}.sdc"
    
    # Analyze RTL
    print(f"Analyzing RTL: {top_file}")
    analyzer = RTLAnalyzer(rtl_dir, args.top)
    
    if not analyzer.parse_module(top_file):
        print(f"Error: Could not find module '{args.top}' in {top_file}", file=sys.stderr)
        return 1
    
    # Generate SDC
    generator = SDCGenerator(
        analyzer,
        args.period,
        args.uncertainty,
        args.io_delay,
        args.load,
        args.drive_cell,
        args.drive_pin,
        args.transition
    )
    generator.generate(output_file)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
