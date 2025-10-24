#!/usr/bin/env python3
"""Test script to verify PRESS command conversion works correctly."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from macros.parser import parse_macro

def test_press_conversion():
    """Test that PRESS commands are converted to HOLD + SLEEP + RELEASE."""
    
    # Test simple PRESS command
    macro_text = """
# Test PRESS conversion
PRESS A 0.1
HOLD B
RELEASE B
"""
    
    commands = parse_macro(macro_text)
    
    print("Original macro:")
    print(macro_text)
    print("\nFlattened commands:")
    for i, (cmd, args) in enumerate(commands):
        print(f"  {i+1}. {cmd} {' '.join(args)}")
    
    # Verify PRESS A 0.1 became HOLD A, SLEEP 0.1, RELEASE A
    expected_start = [
        ('HOLD', ['A']),
        ('SLEEP', ['0.1']),
        ('RELEASE', ['A']),
        ('HOLD', ['B']),
        ('RELEASE', ['B'])
    ]
    
    if commands[:len(expected_start)] == expected_start:
        print("\n✅ PRESS conversion test PASSED!")
    else:
        print("\n❌ PRESS conversion test FAILED!")
        print(f"Expected: {expected_start}")
        print(f"Got: {commands[:len(expected_start)]}")
    
    return commands == expected_start

def test_press_with_loop():
    """Test PRESS commands inside loops are properly converted."""
    
    macro_text = """
LOOP 2
    PRESS A
    PRESS B 0.2
ENDLOOP
"""
    
    commands = parse_macro(macro_text)
    
    print("\n" + "="*50)
    print("Loop test macro:")
    print(macro_text)
    print("\nFlattened commands:")
    for i, (cmd, args) in enumerate(commands):
        print(f"  {i+1}. {cmd} {' '.join(args)}")
    
    # Expected: 2x (HOLD A, SLEEP 0.1, RELEASE A, HOLD B, SLEEP 0.2, RELEASE B)
    expected = [
        # First iteration
        ('HOLD', ['A']),
        ('SLEEP', ['0.1']),  # Default duration
        ('RELEASE', ['A']),
        ('HOLD', ['B']),
        ('SLEEP', ['0.2']),
        ('RELEASE', ['B']),
        # Second iteration
        ('HOLD', ['A']),
        ('SLEEP', ['0.1']),
        ('RELEASE', ['A']),
        ('HOLD', ['B']),
        ('SLEEP', ['0.2']),
        ('RELEASE', ['B']),
    ]
    
    if commands == expected:
        print("\n✅ PRESS loop conversion test PASSED!")
        return True
    else:
        print("\n❌ PRESS loop conversion test FAILED!")
        print(f"Expected length: {len(expected)}, Got length: {len(commands)}")
        return False

if __name__ == "__main__":
    print("Testing PRESS command conversion...")
    
    test1_pass = test_press_conversion()
    test2_pass = test_press_with_loop()
    
    if test1_pass and test2_pass:
        print("\n🎉 All tests PASSED! PRESS conversion is working correctly.")
    else:
        print("\n💥 Some tests FAILED!")
        sys.exit(1)