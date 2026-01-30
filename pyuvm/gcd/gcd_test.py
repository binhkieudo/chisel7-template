"""
GCD Test - Top-level cocotb test with pyUVM
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from pyuvm import *
from gcd_env import GCDEnv
from gcd_sequences import *


# Global DUT reference  
_dut = None


class GCDTestBase(uvm_test):
    """Base test class for GCD verification"""
    
    def build_phase(self):
        global _dut
        self.dut = _dut
        self.env = GCDEnv("env", self, self.dut)
        
    def end_of_elaboration_phase(self):
        """Adjust verbosity after environment is built"""
        # Set to INFO to see detailed test output, CRITICAL to suppress
        self.env.set_logging_level_hier(CRITICAL)
        
    async def run_phase(self):
        """To be overridden by derived tests"""
        raise NotImplementedError("run_phase must be implemented in derived test")


class RandomTest(GCDTestBase):
    """Random test"""
    
    async def run_phase(self):
        self.raise_objection()
        await Timer(1, unit='ns')  # Give time for initialization
        
        # Create and run sequence
        seqr = ConfigDB().get(None, "", "SEQR")
        seq = RandomGCDSequence("random_seq", num_txns=100)
        await seq.start(seqr)
        
        # Wait a bit for final transactions to complete
        for _ in range(10):
            await RisingEdge(self.dut.clock)
        
        self.drop_objection()


class DirectedTest(GCDTestBase):
    """Directed test with known cases"""
    
    async def run_phase(self):
        self.raise_objection()
        await Timer(1, unit='ns')
        
        seqr = ConfigDB().get(None, "", "SEQR")
        seq = DirectedGCDSequence("directed_seq")
        await seq.start(seqr)
        
        for _ in range(10):
            await RisingEdge(self.dut.clock)
        
        self.drop_objection()


class CornerCaseTest(GCDTestBase):
    """Corner case test"""
    
    async def run_phase(self):
        self.raise_objection()
        await Timer(1, unit='ns')
        
        seqr = ConfigDB().get(None, "", "SEQR")
        seq = CornerCaseSequence("corner_seq")
        await seq.start(seqr)
        
        for _ in range(10):
            await RisingEdge(self.dut.clock)
        
        self.drop_objection()


class FullTest(GCDTestBase):
    """Comprehensive test running all sequences"""
    
    async def run_phase(self):
        self.raise_objection()
        await Timer(1, unit='ns')
        
        seqr = ConfigDB().get(None, "", "SEQR")
        
        # Run directed test first
        self.logger.info("Running directed sequence...")
        seq1 = DirectedGCDSequence("directed_seq")
        await seq1.start(seqr)
        
        # Then corner cases
        self.logger.info("Running corner case sequence...")
        seq2 = CornerCaseSequence("corner_seq")
        await seq2.start(seqr)
        
        # Then random
        self.logger.info("Running random sequence...")
        seq3 = RandomGCDSequence("random_seq", num_txns=50)
        await seq3.start(seqr)
        
        # Finally back-to-back stress test
        self.logger.info("Running back-to-back sequence...")
        seq4 = BackToBackSequence("b2b_seq", num_txns=30)
        await seq4.start(seqr)
        
        # Wait for final transactions
        for _ in range(20):
            await RisingEdge(self.dut.clock)
        
        self.drop_objection()


@cocotb.test()
async def gcd_random_test(dut):
    """Run random test"""
    global _dut
    _dut = dut
    
    # Start clock
    cocotb.start_soon(Clock(dut.clock, 10, unit="ns").start())
    
    # Create pyUVM test
    await uvm_root().run_test("RandomTest")


@cocotb.test()
async def gcd_directed_test(dut):
    """Run directed test"""
    global _dut
    _dut = dut
    
    cocotb.start_soon(Clock(dut.clock, 10, unit="ns").start())
    await uvm_root().run_test("DirectedTest")


@cocotb.test()
async def gcd_corner_case_test(dut):
    """Run corner case test"""
    global _dut
    _dut = dut
    
    cocotb.start_soon(Clock(dut.clock, 10, unit="ns").start())
    await uvm_root().run_test("CornerCaseTest")


@cocotb.test()
async def gcd_full_test(dut):
    """Run comprehensive test"""
    global _dut
    _dut = dut
    
    cocotb.start_soon(Clock(dut.clock, 10, unit="ns").start())
    await uvm_root().run_test("FullTest")
