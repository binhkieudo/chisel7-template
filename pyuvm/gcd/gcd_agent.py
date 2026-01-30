"""
GCD Agent
Groups driver and monitor together
"""
from pyuvm import *
from gcd_driver import GCDDriver
from gcd_monitor import GCDMonitor


class GCDAgent(uvm_agent):
    """Agent containing driver and monitor"""
    
    def __init__(self, name, parent, dut):
        super().__init__(name, parent)
        self.dut = dut
        
    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        ConfigDB().set(None, "", "SEQR", self.seqr)
        self.driver = GCDDriver("driver", self, self.dut)
        self.monitor = GCDMonitor("monitor", self, self.dut)
        
    def connect_phase(self):
        """Connect driver and monitor to sequencer"""
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)
