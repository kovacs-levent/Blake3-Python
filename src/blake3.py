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

class Blake3:
    def __init__(self):
        self.chunk_state = ChunkState(IV, 0, 0)
        self.key = IV
        self.cv_stack = []
        self.cv_stack_len = 0
        self.flags = 0

    def push_stack(self, chaining_value):
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
        return (new_cv, chunk_counter)

    def update(self, input):
        while len(input) > 0:
            if self.chunk_state.len() == CHUNK_LEN:
                chunk_cv = self.chunk_state.output().chaining_value()
                total_chunks = self.chunk_state.chunk_counter + 1
                (chunk_cv, total_chunks) = self.add_chunk_value(chunk_cv, total_chunks)
                self.chunk_state = ChunkState(self.key, total_chunks, self.flags)

            want = CHUNK_LEN - self.chunk_state.len()
            take = min(want, len(input))
            self.chunk_state.update(input[:take])
            input = input[take:]

    def finalize(self, out_block):
        output = self.chunk_state.output()
        parent_nodes_remaining = self.cv_stack_len
        print(parent_nodes_remaining)
        while parent_nodes_remaining > 0 :
            parent_nodes_remaining -= 1
            output = parent_output(self.cv_stack[parent_nodes_remaining], output.chaining_value(), self.key, self.flags)
        output.root_output_bytes(out_block)
        byte_output = []
        for b in out_block:
            byte_output.append(b.to_bytes(1, byteorder="little"))
        return b''.join(byte_output)
