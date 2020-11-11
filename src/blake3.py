from Compress import compress
from ChunkState import ChunkState
from ChunkState import Output
IV = [int("0x6A09E667", 16), int("0xBB67AE85", 16), int("0x3C6EF372", 16), int("0xA54FF53A", 16),
int("0x510E527F", 16), int("0x9B05688C", 16), int("0x1F83D9AB", 16), int("0x5BE0CD19", 16)]
BLOCK_SIZE = 64
CHUNK_START = 1
CHUNK_END = 2
PARENT = 4
ROOT = 8
KEYED_HASH = 16
DERIVE_KEY_CONTEXT = 32
DERIVE_KEY_MATERIAL = 64
CHUNK_LEN = 1024

def parent_output(left_cv, right_cv, key, flags):
    block_words = left_cv + right_cv
    return Output(key, block_words, BLOCK_SIZE, 0, PARENT | flags)

def parent_cv(left_cv, right_cv, key, flags):
    return parent_output(left_cv, right_cv, key, flags).chaining_value()

class blake3_hash:
    def __init__(self, key, flags):
        self.chunk_state = ChunkState(key, 0, flags)
        self.key = key
        self.cv_stack = [None]
        self.cv_stack_len = 0
        self.flags = flags

    def push_stack(self, chaining_value):
        if self.cv_stack_len == len(self.cv_stack):
            self.cv_stack.append(chaining_value)
        else:
            self.cv_stack[self.cv_stack_len] = chaining_value
        self.cv_stack_len += 1

    def pop_stack(self):
        self.cv_stack_len -= 1
        return self.cv_stack[self.cv_stack_len]

    def add_chunk_value(self, new_cv, chunk_counter):
        while chunk_counter & 1 == 0:
            new_cv = parent_cv(self.pop_stack(), new_cv, self.key, self.flags)
            chunk_counter >>= 1
        self.push_stack(new_cv)
        return new_cv

    def update(self, input):
        while len(input) > 0:
            if self.chunk_state.len() == CHUNK_LEN:
                chunk_cv = self.chunk_state.output().chaining_value()
                total_chunks = self.chunk_state.chunk_counter + 1
                chunk_cv = self.add_chunk_value(chunk_cv, total_chunks)
                self.chunk_state = ChunkState(self.key, total_chunks, self.flags)

            want = CHUNK_LEN - self.chunk_state.len()
            take = min(want, len(input))
            self.chunk_state.update(input[:take])
            input = input[take:]

    def finalize(self, out_block):
        output = self.chunk_state.output()
        parent_nodes_remaining = self.cv_stack_len
        while parent_nodes_remaining > 0 :
            parent_nodes_remaining -= 1
            output = parent_output(self.cv_stack[parent_nodes_remaining], output.chaining_value(), self.key, self.flags)
        output.root_output_bytes(out_block)
        byte_output = []
        for b in out_block:
            byte_output.append(b.to_bytes(1, byteorder="little"))
        return b''.join(byte_output)

class Blake3:
    def __init__(self, key = IV, mode = "Simple", context = ""):
        self.modes = {"Simple", "Keyed", "Key-Derivation" }
        if mode not in self.modes:
            print("Invalid mode granted")
            exit(1)

        self.mode = mode
        if mode == "Keyed":
            self.key = []
            for b in key:
                self.key.append(b)
            self.key = self.convert_block_to_words(self.key)

        if self.mode == "Key-Derivation":
            self.context = context
            context_hasher = blake3_hash(IV, DERIVE_KEY_CONTEXT)
            context_hasher.update(self.context.encode())
            output = [0] * 32
            self.context_key = context_hasher.finalize(output)
            self.context_key = self.convert_block_to_words(self.context_key)
        self.init_hasher()

    def convert_block_to_words(self, block):
        block_words = []
        for i in range(0, len(block), 4):
            word = int.from_bytes(block[i:i+4], "little")
            block_words.append(word)
        return block_words

    def init_hasher(self):
        if self.mode == "Simple":
            self.hasher = blake3_hash(IV, 0)
        elif self.mode == "Keyed":
            self.hasher = blake3_hash(self.key, KEYED_HASH)
        elif self.mode == "Key-Derivation":
            self.hasher = blake3_hash(self.context_key, DERIVE_KEY_MATERIAL)

    def update(self, input):
        self.hasher.update(input)

    def finalize(self, output):
        return self.hasher.finalize(output)

    def hash(self, input, expected_length = 64):
        self.init_hasher()
        self.hasher.update(input)
        output = [0] * expected_length
        return self.hasher.finalize(output)
