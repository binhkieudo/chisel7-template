"""
GCD Monitor
Monitors the DUT interface and reports transactions
"""
from pyuvm import *
import cocotb
from cocotb.triggers import RisingEdge
from gcd_transaction import GCDTransaction


class GCDMonitor(uvm_component):
    """Monitor for GCD module interface"""
    
    def __init__(self, name, parent, dut):
        super().__init__(name, parent)
        self.dut = dut
        
    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)
        
    async def run_phase(self):
        """Monitor the DUT signals"""
        while True:
            await RisingEdge(self.dut.clock)
            
            # Check if new values are being loaded
            if self.dut.io_loadingValues.value == 1:
                txn = GCDTransaction("monitored_txn")
                txn.value1 = int(self.dut.io_value1.value)
                txn.value2 = int(self.dut.io_value2.value)
                txn.loadingValues = True
                
                # Wait for the result
                max_cycles = 1000
                cycles = 0
                while self.dut.io_outputValid.value == 0 and cycles < max_cycles:
                    await RisingEdge(self.dut.clock)
                    cycles += 1
                
                if cycles < max_cycles:
                    txn.outputGCD = int(self.dut.io_outputGCD.value)
                    txn.outputValid = bool(self.dut.io_outputValid.value)
                    
                    self.logger.debug(f"Monitor observed: {txn}")
                    self.ap.write(txn)
                else:
                    self.logger.warning(f"Monitor timeout on transaction: value1={txn.value1}, value2={txn.value2}")
