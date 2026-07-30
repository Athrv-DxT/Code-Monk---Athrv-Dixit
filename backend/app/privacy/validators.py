import re

# Verhoeff tables for Aadhaar checksum validation
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def verify_verhoeff(number_str: str) -> bool:
    """
    Validates a number string using the Verhoeff algorithm (specifically for Aadhaar).
    """
    clean_num = "".join(c for c in number_str if c.isdigit())
    if len(clean_num) != 12:
        return False
    
    c = 0
    # Reverse clean digits list to process right-to-left
    for i, num in enumerate(reversed(clean_num)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(num)]]
    return c == 0

def verify_luhn(number_str: str) -> bool:
    """
    Validates a card number using the Luhn algorithm.
    """
    clean_num = "".join(c for c in number_str if c.isdigit())
    if not clean_num or len(clean_num) < 13 or len(clean_num) > 19:
        return False
    
    total = 0
    num_digits = len(clean_num)
    oddeven = num_digits & 1
    
    for count in range(num_digits):
        digit = int(clean_num[count])
        if not ((count & 1) ^ oddeven):
            digit = digit * 2
            if digit > 9:
                digit = digit - 9
        total += digit
        
    return (total % 10) == 0

def verify_pan_syntax(pan_str: str) -> bool:
    """
    Validates Indian Permanent Account Number (PAN) syntax.
    Format: 5 letters, 4 digits, 1 letter.
    4th char represents category/status.
    """
    pan_clean = pan_str.strip().upper()
    pan_re = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
    if not pan_re.match(pan_clean):
        return False
    
    status_char = pan_clean[3]
    valid_statuses = {"P", "C", "H", "F", "A", "T", "B", "L", "J", "G"}
    return status_char in valid_statuses
