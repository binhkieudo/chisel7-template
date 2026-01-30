"""
GCD Coverage Collector
Functional coverage for GCD verification
"""
from pyuvm import *
from gcd_transaction import GCDTransaction


class GCDCoverage(uvm_subscriber):
    """Functional coverage collector for GCD"""
    
    def __init__(self, name, parent):
        super().__init__(name, parent)
        # Coverage bins
        self.zero_cases = 0  # One or both values are 0
        self.one_cases = 0  # One value is 1
        self.equal_cases = 0  # Both values equal
        self.coprime_cases = 0  # GCD is 1 (coprime)
        self.max_value_cases = 0  # Contains max 16-bit value
        self.power_of_two_cases = 0  # Values are powers of 2
        self.total_transactions = 0
        
    def write(self, txn):
        """Collect coverage from transaction"""
        self.total_transactions += 1
        
        # Check for zero cases
        if txn.value1 == 0 or txn.value2 == 0:
            self.zero_cases += 1
            
        # Check for one value being 1
        if txn.value1 == 1 or txn.value2 == 1:
            self.one_cases += 1
            
        # Check for equal values
        if txn.value1 == txn.value2:
            self.equal_cases += 1
            
        # Check for coprime (GCD = 1)
        if txn.outputGCD == 1:
            self.coprime_cases += 1
            
        # Check for max value (65535)
        if txn.value1 == 65535 or txn.value2 == 65535:
            self.max_value_cases += 1
            
        # Check for powers of 2
        if self.is_power_of_two(txn.value1) or self.is_power_of_two(txn.value2):
            self.power_of_two_cases += 1
    
    @staticmethod
    def is_power_of_two(n):
        """Check if a number is a power of 2"""
        return n > 0 and (n & (n - 1)) == 0
    
    def report_phase(self):
        """Report coverage statistics"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"COVERAGE REPORT")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total Transactions: {self.total_transactions}")
        self.logger.info(f"Zero cases: {self.zero_cases}")
        self.logger.info(f"One cases: {self.one_cases}")
        self.logger.info(f"Equal values: {self.equal_cases}")
        self.logger.info(f"Coprime (GCD=1): {self.coprime_cases}")
        self.logger.info(f"Max value cases: {self.max_value_cases}")
        self.logger.info(f"Power of 2 cases: {self.power_of_two_cases}")
        self.logger.info(f"{'='*60}\n")
