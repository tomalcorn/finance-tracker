#!/usr/bin/env python3
"""
Random Number Generator Script
Generates and prints a random number between 1 and 10
"""

import random

def get_random_number():
    """Generate and return a random number from 1 to 10"""
    return random.randint(1, 10)

if __name__ == "__main__":
    random_num = get_random_number()
    print(f"Random number from 1 to 10: {random_num}")
