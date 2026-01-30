"""
GCD Environment
Top-level UVM environment containing all verification components
"""
from pyuvm import *
from gcd_agent import GCDAgent
from gcd_scoreboard import GCDScoreboard
from gcd_coverage import GCDCoverage


class GCDEnv(uvm_env):
    """Top-level verification environment"""
    
    def __init__(self, name, parent, dut):
        super().__init__(name, parent)
        self.dut = dut
        
    def build_phase(self):
        self.agent = GCDAgent("agent", self, self.dut)
        self.scoreboard = GCDScoreboard("scoreboard", self)
        self.coverage = GCDCoverage("coverage", self)
        
    def connect_phase(self):
        """Connect components via analysis ports"""
        # Connect driver's analysis port to scoreboard and coverage
        # Scoreboard is a uvm_subscriber with built-in analysis_export
        self.agent.driver.ap.connect(self.scoreboard.analysis_export)
        self.agent.driver.ap.connect(self.coverage.analysis_export)
