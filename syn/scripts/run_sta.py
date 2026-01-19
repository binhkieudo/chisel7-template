#!/usr/bin/env python3
"""
Run OpenSTA and parse timing/power results
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, Dict


class STARunner:
    """Run OpenSTA and parse results"""
    
    def __init__(self, netlist: Path, sdc: Path, liberty: Path, top_module: str, report_dir: Path):
        self.netlist = netlist
        self.sdc = sdc
        self.liberty = liberty
        self.top_module = top_module
        self.report_dir = report_dir
        self.sta_script = Path(__file__).parent / "sta_analysis.tcl"
        
    def clean_netlist_for_sta(self) -> Path:
        """Remove formal verification cells that OpenSTA can't parse"""
        # Create a cleaned copy
        cleaned_netlist = self.netlist.parent / f"{self.netlist.stem}_cleaned.v"
        
        # Collect formal cell instance names to remove their defparams
        formal_instances = set()
        
        with open(self.netlist, 'r') as fin:
            for line in fin:
                # Find formal cell instantiations
                match = re.search(r'\\\$(?:check|assert|assume|cover)\s+(\w+)\s*\(', line)
                if match:
                    formal_instances.add(match.group(1))
        
        with open(self.netlist, 'r') as fin, open(cleaned_netlist, 'w') as fout:
            skip_cell = False
            skip_defparam = False
            paren_depth = 0
            
            for line in fin:
                # Check if this is a defparam for a formal cell
                if 'defparam' in line:
                    for inst_name in formal_instances:
                        if f'defparam {inst_name}.' in line:
                            skip_defparam = True
                            break
                
                if skip_defparam:
                    skip_defparam = False
                    continue
                
                # Check if this is a formal verification cell instantiation
                if re.search(r'\\\$(?:check|assert|assume|cover)\s+\w+\s*\(', line):
                    skip_cell = True
                    paren_depth = 1 if '(' in line else 0
                    continue
                
                if skip_cell:
                    # Track parentheses to find end of instantiation
                    paren_depth += line.count('(') - line.count(')')
                    if paren_depth <= 0 and ');' in line:
                        skip_cell = False
                    continue
                
                fout.write(line)
        
        return cleaned_netlist
        
    def run_sta(self) -> bool:
        """Run OpenSTA analysis"""
        if not self.netlist.exists():
            print(f"Error: Netlist not found: {self.netlist}", file=sys.stderr)
            return False
        
        if not self.liberty.exists():
            print(f"Error: Liberty file not found: {self.liberty}", file=sys.stderr)
            return False
        
        # Clean netlist to remove formal cells
        print("Cleaning netlist for STA...")
        cleaned_netlist = self.clean_netlist_for_sta()
        
        # Set environment variables for STA script
        env = os.environ.copy()
        env['NETLIST_FILE'] = str(cleaned_netlist.absolute())
        env['SDC_FILE'] = str(self.sdc.absolute()) if self.sdc.exists() else ""
        env['LIBERTY_FILE'] = str(self.liberty.absolute())
        env['TOP_MODULE'] = self.top_module
        env['REPORT_DIR'] = str(self.report_dir.absolute())
        
        try:
            # Run STA
            result = subprocess.run(
                ['sta', '-no_splash', '-exit', str(self.sta_script)],
                env=env,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Clean up temporary file
            if cleaned_netlist.exists():
                cleaned_netlist.unlink()
            
            if result.returncode != 0:
                print(f"STA failed with return code {result.returncode}", file=sys.stderr)
                if result.stderr:
                    print(f"Error output: {result.stderr}", file=sys.stderr)
                if result.stdout:
                    print(f"Standard output: {result.stdout}", file=sys.stderr)
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            print("STA timed out after 120 seconds", file=sys.stderr)
            if cleaned_netlist.exists():
                cleaned_netlist.unlink()
            return False
        except FileNotFoundError:
            print("Error: 'sta' command not found. Please install OpenSTA.", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error running STA: {e}", file=sys.stderr)
            if cleaned_netlist.exists():
                cleaned_netlist.unlink()
            return False
    
    def parse_timing_report(self) -> Dict[str, float]:
        """Parse timing report and extract key metrics"""
        timing_rpt = self.report_dir / f"{self.top_module}_sta_timing.rpt"
        
        results = {
            'wns_max': None,  # Worst negative slack (setup)
            'tns_max': None,  # Total negative slack (setup)
            'wns_min': None,  # Worst negative slack (hold)
            'max_freq_mhz': None,  # Maximum achievable frequency
            'target_period_ns': None,
        }
        
        if not timing_rpt.exists():
            return results
        
        with open(timing_rpt, 'r') as f:
            content = f.read()
        
        # Parse WNS (Worst Negative Slack)
        wns_pattern = r'wns\s+([-\d.]+)'
        match = re.search(wns_pattern, content, re.IGNORECASE)
        if match:
            results['wns_max'] = float(match.group(1))
        
        # Parse TNS (Total Negative Slack)
        tns_pattern = r'tns\s+([-\d.]+)'
        match = re.search(tns_pattern, content, re.IGNORECASE)
        if match:
            results['tns_max'] = float(match.group(1))
        
        # Parse max frequency
        freq_pattern = r'Max Frequency:\s+([\d.]+)\s+MHz'
        match = re.search(freq_pattern, content)
        if match:
            results['max_freq_mhz'] = float(match.group(1))
        
        # Parse target frequency
        target_freq_pattern = r'Target Frequency:\s+([\d.]+)\s+MHz'
        match = re.search(target_freq_pattern, content)
        if match:
            target_freq = float(match.group(1))
            results['target_period_ns'] = 1000.0 / target_freq if target_freq > 0 else None
        
        # Parse period
        period_pattern = r'Period:\s+([\d.]+)\s+ns'
        match = re.search(period_pattern, content)
        if match:
            results['target_period_ns'] = float(match.group(1))
        
        return results
    
    def parse_power_report(self) -> Dict[str, float]:
        """Parse power report and extract power metrics"""
        power_rpt = self.report_dir / f"{self.top_module}_sta_power.rpt"
        
        results = {
            'internal_power_mw': None,
            'switching_power_mw': None,
            'leakage_power_mw': None,
            'total_power_mw': None,
        }
        
        if not power_rpt.exists():
            return results
        
        with open(power_rpt, 'r') as f:
            content = f.read()
        
        # Parse power values
        # OpenSTA reports power in various units, need to handle W, mW, uW
        
        # Total power pattern
        total_pattern = r'Total\s+Power.*?([0-9.]+)\s*(W|mW|uW|nW)'
        match = re.search(total_pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            results['total_power_mw'] = self._convert_to_mw(value, unit)
        
        # Internal power
        internal_pattern = r'Internal\s+Power.*?([0-9.]+)\s*(W|mW|uW|nW)'
        match = re.search(internal_pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            results['internal_power_mw'] = self._convert_to_mw(value, unit)
        
        # Switching power
        switching_pattern = r'Switching\s+Power.*?([0-9.]+)\s*(W|mW|uW|nW)'
        match = re.search(switching_pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            results['switching_power_mw'] = self._convert_to_mw(value, unit)
        
        # Leakage power
        leakage_pattern = r'Leakage\s+Power.*?([0-9.]+)\s*(W|mW|uW|nW)'
        match = re.search(leakage_pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            results['leakage_power_mw'] = self._convert_to_mw(value, unit)
        
        return results
    
    def _convert_to_mw(self, value: float, unit: str) -> float:
        """Convert power to milliwatts"""
        unit = unit.upper()
        if unit == 'W':
            return value * 1000.0
        elif unit == 'MW':
            return value
        elif unit == 'UW':
            return value / 1000.0
        elif unit == 'NW':
            return value / 1000000.0
        else:
            return value
    
    def format_power(self, watts: float) -> str:
        """Format power value with appropriate unit"""
        if watts >= 1.0:
            return f"{watts:.3f} W"
        elif watts >= 0.001:
            return f"{watts * 1000:.3f} mW"
        elif watts >= 0.000001:
            return f"{watts * 1000000:.3f} µW"
        else:
            return f"{watts * 1000000000:.3f} nW"
    
    def pretty_print_sta_summary(self):
        """Pretty print STA timing and power summary"""
        timing = self.parse_timing_report()
        power = self.parse_power_report()
        
        # Parse power report for detailed breakdown
        power_rpt = self.report_dir / f"{self.top_module}_sta_power.rpt"
        sequential_power = None
        combinational_power = None
        total_power_w = None
        
        if power_rpt.exists():
            with open(power_rpt, 'r') as f:
                content = f.read()
            
            # Parse individual power components
            seq_match = re.search(r'Sequential\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)', content)
            if seq_match:
                sequential_power = float(seq_match.group(4))
            
            comb_match = re.search(r'Combinational\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)', content)
            if comb_match:
                combinational_power = float(comb_match.group(4))
            
            total_match = re.search(r'Total\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)', content)
            if total_match:
                total_power_w = float(total_match.group(4))
        
        # Parse timing report for detailed info
        timing_rpt = self.report_dir / f"{self.top_module}_sta_timing.rpt"
        wns = None
        tns = None
        target_period = None
        
        if timing_rpt.exists():
            with open(timing_rpt, 'r') as f:
                content = f.read()
            
            wns_match = re.search(r'worst\s+slack\s+max\s+([-\d.]+)', content)
            if wns_match:
                wns = float(wns_match.group(1))
            
            tns_match = re.search(r'tns\s+max\s+([-\d.]+)', content)
            if tns_match:
                tns = float(tns_match.group(1))
            
            period_match = re.search(r'(\d+\.?\d*)\s+ns.*clock.*\(rise edge\)', content)
            if period_match:
                target_period = float(period_match.group(1))
        
        # Print formatted summary
        print("\n" + "="*70)
        print("  OpenSTA Timing & Power Analysis Summary")
        print("="*70)
        
        # Timing section
        print("\n📊 TIMING ANALYSIS")
        print("-" * 70)
        
        GREEN = "\033[92m"
        RED = "\033[91m"
        RESET = "\033[0m"
        
        if wns is not None:
            if wns >= 0:
                status = f"{GREEN}✅ MET{RESET}"
            else:
                status = f"{RED}❌ VIOLATED{RESET}"
            print(f"  Worst Negative Slack (WNS) : {wns:8.3f} ns   {status}")
        if tns is not None:
            print(f"  Total Negative Slack (TNS) : {tns:8.3f} ns")
        
        if target_period and wns is not None:
            if wns < 0:
                achieved_period = target_period - wns
            else:
                achieved_period = target_period
            max_freq = 1000.0 / achieved_period
            target_freq = 1000.0 / target_period
            print(f"  Target Clock Period        : {target_period:8.3f} ns   ({target_freq:.1f} MHz)")
            print(f"  Achieved Period            : {achieved_period:8.3f} ns   ({max_freq:.1f} MHz)")
        
        # Power section
        if total_power_w:
            print(f"\n⚡ POWER ANALYSIS")
            print("-" * 70)
            print(f"  Sequential Power           : {self.format_power(sequential_power if sequential_power else 0):>12}")
            print(f"  Combinational Power        : {self.format_power(combinational_power if combinational_power else 0):>12}")
            print(f"  Total Power                : {self.format_power(total_power_w):>12}")
        
        print("="*70 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Run OpenSTA and parse results')
    parser.add_argument('-n', '--netlist', required=True, help='Synthesized netlist file')
    parser.add_argument('-s', '--sdc', required=True, help='SDC constraints file')
    parser.add_argument('-l', '--liberty', required=True, help='Liberty timing file')
    parser.add_argument('-t', '--top', required=True, help='Top module name')
    parser.add_argument('-r', '--report-dir', default='reports', help='Report directory')
    
    args = parser.parse_args()
    
    runner = STARunner(
        Path(args.netlist),
        Path(args.sdc),
        Path(args.liberty),
        args.top,
        Path(args.report_dir)
    )
    
    print("Running OpenSTA...")
    if runner.run_sta():
        print("✓ STA complete")
        
        # Print pretty summary
        runner.pretty_print_sta_summary()
    else:
        print("✗ STA failed", file=sys.stderr)
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
