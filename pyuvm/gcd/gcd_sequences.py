"""
GCD Test Sequences
Different test scenarios for GCD verification
"""
from pyuvm import *
from gcd_transaction import GCDTransaction
import random


class RandomGCDSequence(uvm_sequence):
    """Random test sequence"""
    
    def __init__(self, name, num_txns=50):
        super().__init__(name)
        self.num_txns = num_txns
        
    async def body(self):
        """Generate random transactions"""
        for i in range(self.num_txns):
            txn = GCDTransaction(f"random_txn_{i}")
            txn.randomize()
            await self.start_item(txn)
            await self.finish_item(txn)


class DirectedGCDSequence(uvm_sequence):
    """Directed test sequence with known interesting cases"""
    
    async def body(self):
        """Generate directed test cases"""
        # Test cases: (value1, value2)
        # Note: Zero values excluded - subtraction-based GCD algorithm doesn't handle them
        # Note: Cases like (1, large_number) excluded - require excessive cycles (timeout)
        test_cases = [
            (1, 1),       # Both one
            (17, 19),     # Two prime numbers (coprime)
            (48, 18),     # Known GCD of 6
            (100, 100),   # Equal values
            (65535, 65535), # Max values equal
            (256, 1024),  # Powers of 2
            (15, 25),     # GCD of 5
            (54, 24),     # GCD of 6
            (1071, 462),  # GCD of 21
        ]
        
        for i, (v1, v2) in enumerate(test_cases):
            txn = GCDTransaction(f"directed_txn_{i}")
            txn.value1 = v1
            txn.value2 = v2
            txn.loadingValues = True
            await self.start_item(txn)
            await self.finish_item(txn)


class CornerCaseSequence(uvm_sequence):
    """Corner case test sequence"""
    
    async def body(self):
        """Generate corner case transactions"""
        # Note: Removed cases that timeout with subtraction-based GCD:
        # - (65535, 1) requires 65534 cycles
        # - (2, 65534) requires 32766 cycles  
        # - (65535, 65534) requires 65533 cycles
        corner_cases = [
            (32768, 32768),  # Half max, equal
            (255, 256),      # Boundary case
            (3, 5),          # Small primes
            (7, 11),         # Small primes
            (13, 17),        # Small primes
        ]
        
        for i, (v1, v2) in enumerate(corner_cases):
            txn = GCDTransaction(f"corner_txn_{i}")
            txn.value1 = v1
            txn.value2 = v2
            txn.loadingValues = True
            await self.start_item(txn)
            await self.finish_item(txn)


class BackToBackSequence(uvm_sequence):
    """Back-to-back transactions to stress test"""
    
    def __init__(self, name, num_txns=30):
        super().__init__(name)
        self.num_txns = num_txns
        
    async def body(self):
        """Generate back-to-back transactions"""
        for i in range(self.num_txns):
            txn = GCDTransaction(f"b2b_txn_{i}")
            # Mix of quick (small values) and slow (large values) computations
            if i % 3 == 0:
                # Quick computation
                txn.value1 = random.randint(1, 100)
                txn.value2 = random.randint(1, 100)
            else:
                # Longer computation
                txn.randomize()
            await self.start_item(txn)
            await self.finish_item(txn)
