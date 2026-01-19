#!/usr/bin/env python3
"""
Parse Yosys synthesis reports and pretty-print key metrics
Uses SQLite database for accurate cell type identification
"""

import argparse
import json
import re
import sys
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple

# Import STA runner if available
try:
    from run_sta import STARunner
    STA_AVAILABLE = True
except ImportError:
    STA_AVAILABLE = False


class CellDatabase:
    """Interface to SQLite cell database for cell type information"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.cell_cache = {}
        
        if db_path.exists():
            try:
                self.conn = sqlite3.connect(str(db_path))
                self._load_cache()
            except sqlite3.Error as e:
                print(f"Warning: Could not connect to cell database: {e}", file=sys.stderr)
                self.conn = None
    
    def _load_cache(self):
        """Load all HD cells into cache for faster lookup"""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        # Only load sky130_fd_sc_hd cells (high-density standard cells)
        cursor.execute("""
            SELECT cell_name, cell_type 
            FROM cells 
            WHERE cell_name LIKE 'sky130_fd_sc_hd%'
        """)
        
        for cell_name, cell_type in cursor.fetchall():
            self.cell_cache[cell_name] = cell_type
    
    def get_cell_type(self, cell_name: str) -> Optional[str]:
        """Get cell type from database"""
        return self.cell_cache.get(cell_name)
    
    def get_ff_features(self, cell_name: str) -> Tuple[bool, str]:
        """
        Determine if cell is a flip-flop and its features
        
        Returns:
            (is_ff, features_str) where features_str describes the FF type
        """
        cell_type = self.get_cell_type(cell_name)
        
        # Check if it's a sequential cell or logic (dfXXX cells)
        if not cell_type:
            return (False, "")
        
        is_sequential = cell_type.startswith('sequential')
        
        # Check cell name for flip-flop patterns
        is_ff = bool(re.search(r'(e|se)?df[a-z]*[trb]p', cell_name))
        
        if not is_ff:
            return (False, "")
        
        # Determine FF features from cell name and database type
        features = []
        
        # Check for scan
        if cell_name.startswith('sky130_fd_sc_hd__sdf') or cell_name.startswith('sky130_fd_sc_hd__sedf'):
            features.append("Scan")
        
        # Check for enable
        if 'edf' in cell_name:
            features.append("Enable")
        
        # Check database cell_type for reset/set
        if cell_type == 'sequential_r':
            features.append("Reset")
        elif cell_type == 'sequential_s':
            features.append("Set")
        elif cell_type == 'sequential_rs':
            features.append("Reset+Set")
        else:
            # Fallback: check cell name if database doesn't classify it properly
            # dfrtp = reset, dfstp = set, dfrbp/dfsbp = both
            if 'dfrtp' in cell_name or 'dfrbp' in cell_name:
                if "Reset" not in features:
                    features.append("Reset")
            if 'dfstp' in cell_name or 'dfsbp' in cell_name:
                if "Set" not in features:
                    features.append("Set")
        
        # Build feature string
        if features:
            return (True, f"FF/{'/'.join(features)}")
        else:
            return (True, "FF")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SynthesisReport:
    """Container for synthesis metrics"""
    
    def __init__(self):
        self.logic_elements = 0
        self.flip_flops = 0
        self.reset_ffs = 0
        self.reset_ffs = 0
        self.latches = 0
        self.buffers = 0
        self.area = 0.0
        self.cells = {}
        self.hierarchy_depth = 0
        
        # STA results
        self.sta_max_freq_mhz = None
        self.sta_wns_ns = None
        self.sta_tns_ns = None
        self.sta_power_mw = None
        self.sta_available = False
        
    def __str__(self):
        return f"Logic: {self.logic_elements}, FFs: {self.flip_flops}, Area: {self.area:.2f}"


class ReportParser:
    """Parse Yosys synthesis reports"""
    
    def __init__(self, report_dir: Path, top_module: str, cell_db: Optional[CellDatabase] = None):
        self.report_dir = report_dir
        self.top_module = top_module
        self.cell_db = cell_db
        self.report = SynthesisReport()
        
    def parse_stats_file(self) -> bool:
        """Parse the main statistics file"""
        stats_file = self.report_dir / f"{self.top_module}_stats.txt"
        
        if not stats_file.exists():
            print(f"Error: Statistics file not found: {stats_file}", file=sys.stderr)
            return False
        
        with open(stats_file, 'r') as f:
            content = f.read()
        
        # Parse cell counts
        # Yosys format: COUNT  AREA  CELL_NAME
        # Look for lines like "      191 4.78E+03   sky130_fd_sc_hd__dfrtp_1"
        cell_pattern = r'\s+(\d+)\s+[\d.E+]+\s+(sky130_fd_sc_hd__\w+)'
        for match in re.finditer(cell_pattern, content):
            cell_count = int(match.group(1))
            cell_name = match.group(2)
            self.report.cells[cell_name] = cell_count
        
        # Count different cell types
        self._categorize_cells()
        
        # Parse area if available
        area_pattern = r'Chip area for.*?:\s*([\d.]+)'
        area_match = re.search(area_pattern, content)
        if area_match:
            self.report.area = float(area_match.group(1))
        
        # Parse number of wires, cells, etc.
        wire_pattern = r'Number of wires:\s*(\d+)'
        wire_match = re.search(wire_pattern, content)
        
        cell_count_pattern = r'Number of cells:\s*(\d+)'
        cell_count_match = re.search(cell_count_pattern, content)
        
        return True
    
    def _categorize_cells(self):
        """Categorize cells into logic, FFs, etc."""
        for cell_name, count in self.report.cells.items():
            # Use database if available
            if self.cell_db:
                is_ff, _ = self.cell_db.get_ff_features(cell_name)
                
                if is_ff:
                    self.report.flip_flops += count
                    
                    # Check if it has reset/set features
                    cell_type = self.cell_db.get_cell_type(cell_name)
                    if cell_type in ['sequential_r', 'sequential_s', 'sequential_rs']:
                        self.report.reset_ffs += count
                    else:
                        # Fallback: check cell name for reset/set features
                        if ('dfrtp' in cell_name or 'dfstp' in cell_name or 
                            'dfrbp' in cell_name or 'dfsbp' in cell_name):
                            self.report.reset_ffs += count
                # Latches
                elif 'dlatch' in cell_name or 'latch' in cell_name:
                    self.report.latches += count
                # Logic gates
                elif any(gate in cell_name for gate in ['and', 'or', 'nand', 'nor', 'xor', 'xnor',
                                                          'buf', 'inv', 'mux', 'maj', 'ha', 'fa']):
                    self.report.logic_elements += count
                    if 'buf' in cell_name:
                        self.report.buffers += count
            else:
                # Fallback to regex patterns if no database
                # Detect flip-flops
                # SKY130 FF naming: df<features><edge><polarity>
                # Examples: dfxtp (basic), dfrtp (reset), dfstp (set), edfxtp (enable)
                # Pattern matches: dfXXp, dfrtp, dfstp, dfrbp, dfsbp, edfxtp, edfrtp, etc.
                if re.search(r'(e)?df[a-z]*[trb]p', cell_name):
                    self.report.flip_flops += count
                    
                    # Check for reset/set FFs
                    # These have 'r' (reset), 's' (set), or 'b' (both) in the name
                    # Examples: dfrtp, dfstp, dfrbp, dfsbp, edfrtp, edfstp
                    if re.search(r'df[a-z]*[rsb][trb]p', cell_name):
                        self.report.reset_ffs += count
                
                # Latches
                elif 'dlatch' in cell_name or 'latch' in cell_name:
                    self.report.latches += count
                
                # Logic gates (and, or, nand, nor, xor, etc.)
                elif any(gate in cell_name for gate in ['and', 'or', 'nand', 'nor', 'xor', 'xnor', 
                                                          'buf', 'inv', 'mux', 'maj', 'ha', 'fa']):
                    self.report.logic_elements += count
                    if 'buf' in cell_name:
                        self.report.buffers += count
    
    def parse_json_stats(self) -> bool:
        """Parse JSON statistics file (if available)"""
        json_file = self.report_dir / f"{self.top_module}_stats.json"
        
        if not json_file.exists():
            return False
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Extract additional metrics from JSON if needed
            # JSON format varies, this is a placeholder for future enhancement
            
        except json.JSONDecodeError:
            print(f"Warning: Could not parse JSON file: {json_file}", file=sys.stderr)
            return False
        
        return True
    
    def parse_sta_reports(self) -> bool:
        """Parse STA timing and power reports if available"""
        timing_rpt = self.report_dir / f"{self.top_module}_sta_timing.rpt"
        power_rpt = self.report_dir / f"{self.top_module}_sta_power.rpt"
        
        if not timing_rpt.exists() or timing_rpt.stat().st_size == 0:
            return False
        
        self.report.sta_available = True
        
        # Parse timing report
        try:
            with open(timing_rpt, 'r') as f:
                timing_content = f.read()
            
            # Parse WNS (Worst Negative Slack) - format: "worst slack max -0.05"
            wns_match = re.search(r'worst\s+slack\s+max\s+([-\d.]+)', timing_content, re.IGNORECASE)
            if wns_match:
                self.report.sta_wns_ns = float(wns_match.group(1))
            
            # Parse TNS (Total Negative Slack) - format: "tns max -0.90"
            tns_match = re.search(r'tns\s+max\s+([-\d.]+)', timing_content, re.IGNORECASE)
            if tns_match:
                self.report.sta_tns_ns = float(tns_match.group(1))
            
            # Estimate max frequency from WNS
            # If we have clock period info, calculate achieved frequency
            # Look for clock period in the report - format: "10.000   10.000   clock io_blockClock (rise edge)"
            # Avoid matching "0.000   0.000" which are delays, not clock periods
            period_match = re.search(r'^\s+([1-9]\d*\.?\d*)\s+\1\s+clock\s+\w+\s+\(rise edge\)', timing_content, re.MULTILINE)
            if period_match and self.report.sta_wns_ns is not None:
                target_period = float(period_match.group(1))
                achieved_period = target_period - self.report.sta_wns_ns
                self.report.sta_max_freq_mhz = 1000.0 / achieved_period if achieved_period > 0 else None
                
        except Exception as e:
            print(f"Warning: Error parsing timing report: {e}", file=sys.stderr)
        
        # Parse power report
        if power_rpt.exists():
            try:
                with open(power_rpt, 'r') as f:
                    power_content = f.read()
                
                # Parse total power - format: "Total   1.24e-02   2.48e-03 ..."
                # Look for the Total line in power report
                total_match = re.search(r'Total\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)', power_content)
                if total_match:
                    # Column 4 is total power in Watts
                    total_power_w = float(total_match.group(4))
                    self.report.sta_power_mw = total_power_w * 1000.0  # Convert to mW
                        
            except Exception as e:
                print(f"Warning: Error parsing power report: {e}", file=sys.stderr)
        
        return True
    
    def estimate_power(self) -> float:
        """Estimate dynamic power based on cell counts
        
        This is a rough estimate. For accurate power analysis, use specialized tools.
        """
        # Rough power estimates per cell type (in µW at 100MHz, 1.8V)
        power_per_cell = {
            'ff': 5.0,      # Flip-flop
            'logic': 2.0,   # Logic gate
            'latch': 4.0,   # Latch
        }
        
        total_power = 0.0
        total_power += self.report.flip_flops * power_per_cell['ff']
        total_power += self.report.logic_elements * power_per_cell['logic']
        total_power += self.report.latches * power_per_cell['latch']
        
        # Convert to mW
        return total_power / 1000.0
    
    def estimate_frequency(self) -> float:
        """Estimate maximum frequency
        
        This is a very rough estimate based on logic depth.
        For accurate timing, use OpenSTA or other STA tools.
        """
        # Rough heuristic: smaller designs can typically run faster
        # This is just a placeholder - real timing analysis is needed
        
        if self.report.logic_elements < 1000:
            return 200.0  # MHz
        elif self.report.logic_elements < 5000:
            return 150.0
        elif self.report.logic_elements < 10000:
            return 100.0
        else:
            return 75.0
    
    def print_summary(self, detailed: bool = False):
        """Pretty-print the synthesis summary"""
        
        # Box drawing characters
        box_chars = {
            'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
            'h': '═', 'v': '║', 'vr': '╠', 'vl': '╣', 'hd': '╦', 'hu': '╩', 'c': '╬'
        }
        
        width = 50
        
        # Header
        print(box_chars['tl'] + box_chars['h'] * width + box_chars['tr'])
        print(f"{box_chars['v']}{'Synthesis Results Summary':^{width}}{box_chars['v']}")
        print(f"{box_chars['v']}{f'Module: {self.top_module}':^{width}}{box_chars['v']}")
        print(box_chars['vr'] + box_chars['h'] * width + box_chars['vl'])
        
        # Metrics - use STA data if available
        metrics = [
            ("Logic Elements", f"{self.report.logic_elements:,}"),
            ("Flip-Flops (Total)", f"{self.report.flip_flops:,}"),
            ("Reset FFs", f"{self.report.reset_ffs:,}"),
            ("Latches", f"{self.report.latches:,}"),
            ("Buffers", f"{self.report.buffers:,}"),
            ("", ""),  # Separator
        ]
        
        # Add frequency metrics
        if self.report.sta_available and self.report.sta_max_freq_mhz:
            metrics.append(("Max Frequency (STA)", f"{self.report.sta_max_freq_mhz:.1f} MHz"))
            # Also show estimate for comparison
            est_freq = self.estimate_frequency()
            metrics.append(("Est. Max Frequency", f"{est_freq:.1f} MHz"))
        else:
            est_freq = self.estimate_frequency()
            metrics.append(("Est. Max Frequency", f"{est_freq:.1f} MHz"))
        
        # Add power metrics
        if self.report.sta_available and self.report.sta_power_mw:
            metrics.append(("Total Power (STA)", f"{self.report.sta_power_mw:.2f} mW"))
        else:
            est_power = self.estimate_power()
            metrics.append(("Est. Power @ 100MHz", f"{est_power:.2f} mW"))
        
        # Add STA timing details if available
        if self.report.sta_available:
            if self.report.sta_wns_ns is not None:
                metrics.append(("WNS (Setup)", f"{self.report.sta_wns_ns:.3f} ns"))
            if self.report.sta_tns_ns is not None:
                metrics.append(("TNS (Setup)", f"{self.report.sta_tns_ns:.3f} ns"))
        
        # Add area
        metrics.append(("Total Area", f"{self.report.area:.1f} µm²"))
        
        for label, value in metrics:
            if label == "":
                print(box_chars['vr'] + box_chars['h'] * width + box_chars['vl'])
            else:
                print(f"{box_chars['v']} {label:<22}: {value:>{width-26}} {box_chars['v']}")
        
        print(box_chars['bl'] + box_chars['h'] * width + box_chars['br'])
        
        # Detailed cell breakdown
        if detailed and self.report.cells:
            print("\n" + "="*60)
            print("Detailed Cell Breakdown")
            print("="*60)
            
            # Sort cells by count (descending)
            sorted_cells = sorted(self.report.cells.items(), key=lambda x: x[1], reverse=True)
            
            print(f"{'Cell Type':<40} {'Count':>10}")
            print("-"*60)
            for cell_name, count in sorted_cells[:20]:  # Top 20
                # Shorten cell name for display
                short_name = cell_name.replace('sky130_fd_sc_hd__', '')
                
                # Add annotations using database if available
                annotation = ""
                if self.cell_db:
                    is_ff, ff_features = self.cell_db.get_ff_features(cell_name)
                    if is_ff:
                        annotation = f" ({ff_features})"
                else:
                    # Fallback to regex-based annotation
                    if re.search(r'(e)?df[a-z]*[trb]p', cell_name):
                        # It's a flip-flop
                        if re.search(r'df[a-z]*[rsb][trb]p', cell_name):
                            annotation = " (Reset FF)"
                        else:
                            annotation = " (FF)"
                
                # Format with annotation
                cell_display = f"{short_name}{annotation}"
                print(f"{cell_display:<40} {count:>10,}")
            
            if len(sorted_cells) > 20:
                remaining = len(sorted_cells) - 20
                remaining_count = sum(count for _, count in sorted_cells[20:])
                print(f"{'... and ' + str(remaining) + ' more':<40} {remaining_count:>10,}")
            
            print("-"*60)
            print(f"{'Total Cells':<40} {sum(self.report.cells.values()):>10,}")
            print("="*60)
        
        # Warnings
        if self.report.latches > 0:
            print("\n⚠️  Warning: Design contains latches. Consider using flip-flops instead.")
        
        if self.report.area == 0:
            print("\n⚠️  Note: Area information not available. Check liberty file loading.")
        
        if not self.report.sta_available:
            print(f"\n💡 For accurate timing and power analysis, run 'make sta' with OpenSTA.")
        else:
            # Timing Status Announcement
            GREEN = "\033[92m"
            RED = "\033[91m"
            RESET = "\033[0m"
            
            if self.report.sta_wns_ns is not None:
                if self.report.sta_wns_ns >= 0:
                    print(f"\n{GREEN}✅ SUCCESS: Timing constraints met!{RESET}")
                    print(f"{GREEN}   Achieved Max Frequency: {self.report.sta_max_freq_mhz:.2f} MHz{RESET}")
                else:
                    print(f"\n{RED}❌ FAILURE: Timing constraints VIOLATED!{RESET}")
                    print(f"{RED}   Achieved Max Frequency: {self.report.sta_max_freq_mhz:.2f} MHz{RESET}")
                    print(f"{RED}   Worst Negative Slack:  {self.report.sta_wns_ns:.3f} ns{RESET}")
            
            print(f"\n✓ Timing and power analysis completed using OpenSTA.")


def main():
    parser = argparse.ArgumentParser(
        description='Parse and display Yosys synthesis reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Parse and display summary
  %(prog)s -t MemoryAdapterMsgSync -r reports
  
  # Show detailed cell breakdown
  %(prog)s -t MemoryAdapterMsgSync -r reports --detailed
        '''
    )
    
    parser.add_argument('-t', '--top', required=True,
                        help='Top module name')
    parser.add_argument('-r', '--report-dir', default='reports',
                        help='Report directory (default: reports)')
    parser.add_argument('-d', '--detailed', action='store_true',
                        help='Show detailed cell breakdown')
    parser.add_argument('--db', default='db/cells.db',
                        help='Path to cell database (default: db/cells.db)')
    
    args = parser.parse_args()
    
    # Parse reports
    report_dir = Path(args.report_dir)
    if not report_dir.exists():
        print(f"Error: Report directory not found: {report_dir}", file=sys.stderr)
        return 1
    
    # Initialize cell database
    db_path = Path(args.db)
    cell_db = None
    if db_path.exists():
        cell_db = CellDatabase(db_path)
        if cell_db.conn:
            print(f"✓ Loaded cell database: {db_path} ({len(cell_db.cell_cache)} cells)", file=sys.stderr)
    else:
        print(f"⚠️  Cell database not found: {db_path}. Using regex-based cell detection.", file=sys.stderr)
    
    try:
        parser_obj = ReportParser(report_dir, args.top, cell_db)
        
        if not parser_obj.parse_stats_file():
            return 1
        
        # Try to parse JSON stats
        parser_obj.parse_json_stats()
        
        # Try to parse STA reports
        parser_obj.parse_sta_reports()
        
        # Display summary
        parser_obj.print_summary(detailed=args.detailed)
    finally:
        if cell_db:
            cell_db.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
