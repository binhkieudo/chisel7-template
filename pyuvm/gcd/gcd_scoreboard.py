"""
GCD Scoreboard
Compares DUT output against expected values
"""
from pyuvm import *
import math
from gcd_transaction import GCDTransaction


class GCDScoreboard(uvm_subscriber):
    """Scoreboard to verify GCD results"""
    
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.passed = 0
        self.failed = 0
        
    def write(self, txn):
        """Called by analysis port when transaction is available"""
        self.check_transaction(txn)
    
    def check_transaction(self, txn):
        """Verify a single transaction"""
        # Calculate expected GCD using Python's math.gcd
        expected_gcd = math.gcd(txn.value1, txn.value2)
        
        if txn.outputGCD == expected_gcd and txn.outputValid:
            self.passed += 1
            self.logger.debug(f"PASS: GCD({txn.value1}, {txn.value2}) = {txn.outputGCD} (expected {expected_gcd})")
        else:
            self.failed += 1
            self.logger.error(f"FAIL: GCD({txn.value1}, {txn.value2}) = {txn.outputGCD} (expected {expected_gcd}), outputValid={txn.outputValid}")
            
    def report_phase(self):
        """Report final statistics"""
        total = self.passed + self.failed
        if total > 0:
            pass_rate = (self.passed / total) * 100
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"SCOREBOARD SUMMARY")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"Total Transactions: {total}")
            self.logger.info(f"Passed: {self.passed}")
            self.logger.info(f"Failed: {self.failed}")
            self.logger.info(f"Pass Rate: {pass_rate:.1f}%")
            self.logger.info(f"{'='*60}\n")
            
            if self.failed > 0:
                raise Exception(f"Scoreboard: {self.failed} transaction(s) failed!")
        else:
            self.logger.warning("No transactions checked by scoreboard!")
