import base58

# Example: Your private key as a list of integers
private_key_integers = []

# Convert to bytes
private_key_bytes = bytes(private_key_integers)

# Encode to base58
base58_private_key = base58.b58encode(private_key_bytes).decode("utf-8")
print("Base58-encoded private key:", base58_private_key)
