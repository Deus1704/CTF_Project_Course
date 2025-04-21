# Reverse Engineering Challenge

This challenge requires participants to analyze a binary file and extract a hidden flag.

## Challenge Description

Participants are given a binary file with a custom format. They need to:

1. Understand the file structure
2. Identify the encoded flag
3. Decode the flag using a simple XOR operation

## Solution

The binary file has the following structure:
- Magic header: "REVENG" (6 bytes)
- Version: 2 bytes (little-endian)
- Flag length: 2 bytes (little-endian)
- Random data: 20 bytes (ignore this)
- Encoded flag: [flag_length] bytes
- Checksum: 1 byte (sum of encoded flag bytes mod 256)

The flag is encoded with a simple XOR operation using the key 42 (decimal).

### Python Solution Script

```python
def decode_binary(binary_path):
    with open(binary_path, 'rb') as f:
        data = f.read()
    
    # Check magic header
    if data[:6] != b"REVENG":
        print("Invalid file format")
        return None
    
    # Get flag length
    flag_length = int.from_bytes(data[8:10], byteorder='little')
    
    # Skip header, version, flag length, and random data
    offset = 6 + 2 + 2 + 20
    
    # Extract encoded flag
    encoded_flag = data[offset:offset+flag_length]
    
    # Decode with XOR key 42
    xor_key = 42
    decoded_flag = ''.join([chr(b ^ xor_key) for b in encoded_flag])
    
    return decoded_flag

# Usage
flag = decode_binary("secret_binary")
print(flag)
```

## Difficulty

Medium - Requires basic understanding of binary file formats and simple encoding techniques.
