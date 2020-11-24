import pytest
import json

from blake3_parallel_1 import Blake3


def blake_hash(expected_hash, input_len, mode, key=None, context_string=None):
    if mode == 'hash':
        hasher = Blake3(mode="Simple")
    elif mode == 'keyed_hash':
        hasher = Blake3(key=key.encode(), mode="Keyed")
    elif mode == 'key_derivation':
        hasher = Blake3(mode="Key-Derivation", context=context_string)
    expected_hash_bytes = bytes.fromhex(expected_hash)
    input = []
    for i in range(0, input_len):
        input.append((i % 251).to_bytes(1, byteorder="little"))
    input = b''.join(input)
    hash = hasher.hash(input, len(expected_hash_bytes))
    return hash, expected_hash_bytes


def test_hash():
    mode = 'hash'
    with open('test_vectors.json') as f:
        data = json.load(f)
    for out in data['cases']:
        input_len = out['input_len']
        expected_hash = out['hash']
        hash, expected_hash_bytes = blake_hash(expected_hash, input_len, mode)
        if hash != expected_hash_bytes:
            print(out['input_len'])
        assert hash == expected_hash_bytes


def test_keyed_hash():
    mode = 'keyed_hash'
    with open('test_vectors.json') as f:
        data = json.load(f)
    key = data['key']
    for out in data['cases']:
        input_len = out['input_len']
        expected_hash = out['keyed_hash']
        hash, expected_hash_bytes = blake_hash(expected_hash, input_len, mode, key)
        assert hash == expected_hash_bytes


def test_derive_key():
    mode = 'key_derivation'
    with open('test_vectors.json') as f:
        data = json.load(f)
    context_string = data['context_string']
    for out in data['cases']:
        input_len = out['input_len']
        expected_hash = out['derive_key']
        hash, expected_hash_bytes = blake_hash(expected_hash, input_len, mode, None, context_string)
        assert hash == expected_hash_bytes
