from blake3 import Blake3
import time

key = "whats the Elvish word for friend"
context_string = "BLAKE3 2019-12-27 16:29:52 test vectors context"

hasher = Blake3(mode="Simple")
#hasher = Blake3(key = key.encode(), mode = "Keyed")
#hasher = Blake3(mode = "Key-Derivation", context = context_string)
expected_hash = "62b6960e1a44bcc1eb1a611a8d6235b6b4b78f32e7abc4fb4c6cdcce94895c47860cc51f2b0c28a7b77304bd55fe73af663c02d3f52ea053ba43431ca5bab7bfea2f5e9d7121770d88f70ae9649ea713087d1914f7f312147e247f87eb2d4ffef0ac978bf7b6579d57d533355aa20b8b77b13fd09748728a5cc327a8ec470f4013226f"
expected_hash_bytes = bytes.fromhex(expected_hash)

input_len = 1000000000

input = []
for i in range(0, input_len):
    input.append((i % 251).to_bytes(1, byteorder="little"))
input = b''.join(input)
print("start")
start = time.time()
hash = hasher.hash(input, len(expected_hash_bytes))
end = time.time()
print(end-start)
print(hash == expected_hash_bytes)
