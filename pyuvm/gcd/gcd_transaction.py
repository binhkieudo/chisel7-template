"""
GCD Transaction Class
Defines the transaction item for GCD verification
"""
from pyuvm import *
import random


class GCDTransaction(uvm_sequence_item):
    """Transaction item for GCD operations"""
    
    def __init__(self, name="GCDTransaction"):
        super().__init__(name)
        self.value1 = 0
        self.value2 = 0
        self.loadingValues = False
        self.outputGCD = 0
        self.outputValid = False
        
    def randomize(self):
        """Randomize the input values"""
        # IMPORTANT: Subtraction-based GCD has O(n) complexity where n = max(value1, value2)
        # Large values can cause timeouts. Limit to reasonable range.
        
        # Most transactions use moderate values (1-10000)
        if random.random() < 0.7:
            self.value1 = random.randint(1, 10000)
            self.value2 = random.randint(1, 10000)
        # Some use small values (1-1000)  
        elif random.random() < 0.8:
            self.value1 = random.randint(1, 1000)
            self.value2 = random.randint(1, 1000)
        # Few use larger values but with equal or related values (fast computation)
        else:
            base = random.randint(1, 20000)
            # Make values multiples of base for faster GCD
            self.value1 = base * random.randint(1, 3)
            self.value2 = base * random.randint(1, 3)
        
        self.loadingValues = True
        return self
        
    def __str__(self):
        return f"GCDTransaction(value1={self.value1}, value2={self.value2}, loadingValues={self.loadingValues}, outputGCD={self.outputGCD}, outputValid={self.outputValid})"
    
    def __eq__(self, other):
        if not isinstance(other, GCDTransaction):
            return False
        return (self.value1 == other.value1 and 
                self.value2 == other.value2 and
                self.outputGCD == other.outputGCD and
                self.outputValid == other.outputValid)
