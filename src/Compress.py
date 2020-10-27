bitmask = 2**32-1
IV = [int("0x6A09E667", 16), int("0xBB67AE85", 16), int("0x3C6EF372", 16), int("0xA54FF53A", 16),
int("0x510E527F", 16), int("0x9B05688C", 16), int("0x1F83D9AB", 16), int("0x5BE0CD19", 16)]
MSG_PERMUTATION = [2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8]

def ror(n, rotations, width = 32):
    rotations = rotations % width
    return bitmask & ((n >> rotations) | (n << (width-rotations)))

def rol(n, rotations, width = 32):
    rotations = rotations % width
    return (n << rotations) & bitmask | ((n&bitmask) >> (width-rotations))

#It's assumed that state is passed by reference, it's needed that we don't copy the state
def mix(state, a, b, c, d, mx, my):
    state[a] = (state[a] + state[b] + mx) % (2**32)
    #Rotation, default width is 32 bits
    state[d] = ror(state[d] ^ state[a], 16)
    state[c] = (state[c] + state[d]) % (2**32)
    state[b] = ror(state[b] ^ state[c], 12)

    state[a] = (state[a] + state[b] + my) % (2**32)
    state[d] = ror(state[d] ^ state[a], 8)
    state[c] = (state[c] + state[d]) % (2**32)
    state[b] = ror(state[b] ^ state[c], 7)
    return state

#The state is also here passed by reference
def round(state, message):
    #Column mixing
    state = mix(state, 0, 4, 8, 12, message[0], message[1])
    state = mix(state, 1, 5, 9, 13, message[2], message[3])
    state = mix(state, 2, 6, 10, 14, message[4], message[5])
    state = mix(state, 3, 7, 11, 15, message[6], message[7])
    #Diagonal mixing
    state = mix(state, 0, 5, 10, 15, message[8], message[9])
    state = mix(state, 1, 6, 11, 12, message[10], message[11])
    state = mix(state, 2, 7, 8, 13, message[12], message[13])
    state = mix(state, 3, 4, 9, 14, message[14], message[15])
    return state

def permute(message):
    result = message
    for i in range(0, 16):
        result[i] = message[MSG_PERMUTATION[i]]
    return result

def compress(chaining_value, block_words, counter, block_length, flags):
    #We use this to manually extract the least significant 32 bits from a number which is larger than 32 bits 
    bit_mask32 = int("0xFFFFFFFF", 16)
    state = chaining_value[:8] + IV[:4] + [counter & bit_mask32, (counter >> 32) & bit_mask32, block_length, flags]

    #6 rounds of mixing and permutations
    for _ in range(0, 6):
        state = round(state, block_words)
        block_words = permute(block_words)
    #A final 7th mixing round is needed without permuting the block
    state = round(state, block_words)

    for i in range(0, 8):
        state[i] ^= state[i+8]
        state[i+8] ^= chaining_value[i]

    return state
