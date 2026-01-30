"""
GCD Driver
Drives transactions to the DUT
"""
from pyuvm import *
import cocotb
from cocotb.triggers import RisingEdge, FallingEdge
from gcd_transaction import GCDTransaction


class GCDDriver(uvm_driver):
    """Driver for GCD module"""
    
    def __init__(self, name, parent, dut):
        super().__init__(name, parent)
        self.dut = dut
        
    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)
        
    async def run_phase(self):
        """Drive transactions to the DUT"""
        await self.reset_dut()
        
        while True:
            # Get transaction from sequencer
            txn = await self.seq_item_port.get_next_item()
            self.logger.info(f"Driver received: {txn}")
            
            # Drive the transaction
            await self.drive_transaction(txn)
            
            # Send to analysis port for monitoring
            self.ap.write(txn)
            
            # Notify sequencer that item is done
            self.seq_item_port.item_done()
    
    async def reset_dut(self):
        """Reset the DUT"""
        self.logger.info("Resetting DUT")
        self.dut.reset.value = 1
        self.dut.io_loadingValues.value = 0
        self.dut.io_value1.value = 0
        self.dut.io_value2.value = 0
        
        # Hold reset for 5 cycles
        for _ in range(5):
            await RisingEdge(self.dut.clock)
            
        self.dut.reset.value = 0
        await RisingEdge(self.dut.clock)
        self.logger.info("Reset complete")
        
    async def drive_transaction(self, txn):
        """Drive a single transaction to the DUT"""
        # Assert loadingValues and drive input values
        self.dut.io_loadingValues.value = 1
        self.dut.io_value1.value = txn.value1
        self.dut.io_value2.value = txn.value2
        
        await RisingEdge(self.dut.clock)
        
        # Deassert loadingValues
        self.dut.io_loadingValues.value = 0
        
        # Wait for outputValid to go low (clear from previous transaction)
        # This is critical to avoid reading stale data
        max_wait = 10
        wait_cycles = 0
        while self.dut.io_outputValid.value == 1 and wait_cycles < max_wait:
            await RisingEdge(self.dut.clock)
            wait_cycles += 1
        
        # Now wait for outputValid to be asserted for THIS transaction
        max_cycles = 1000  # Timeout protection
        cycles = 0
        while self.dut.io_outputValid.value == 0 and cycles < max_cycles:
            await RisingEdge(self.dut.clock)
            cycles += 1
            
        if cycles >= max_cycles:
            self.logger.error(f"TIMEOUT waiting for outputValid for transaction {txn}")
        else:
            # Capture output
            txn.outputGCD = int(self.dut.io_outputGCD.value)
            txn.outputValid = bool(self.dut.io_outputValid.value)
            self.logger.info(f"Transaction complete in {cycles} cycles: GCD({txn.value1}, {txn.value2}) = {txn.outputGCD}")
