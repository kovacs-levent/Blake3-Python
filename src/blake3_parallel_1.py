from Compress import compress
from ChunkState import ChunkState
from ChunkState import Output
import math
import concurrent.futures
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
BLOCK_LEN = 64

def dump(chunk_state):
    cv_val = chunk_state.output().chaining_value()
    byte_output = []
    for i in cv_val:
        byte_o = i.to_bytes(4, byteorder="little")
        byte_output.append(byte_o[0])
        byte_output.append(byte_o[1])
        byte_output.append(byte_o[2])
        byte_output.append(byte_o[3])
    print(byte_output)

def dump_cv(cv_val):
    byte_output = []
    for i in cv_val:
        byte_o = i.to_bytes(4, byteorder="little")
        byte_output.append(byte_o[0])
        byte_output.append(byte_o[1])
        byte_output.append(byte_o[2])
        byte_output.append(byte_o[3])
    print(byte_output)

OUT_LEN = 8
THREAD_COUNT = 2


def parent_output(left_cv, right_cv, key, flags):
    block_words = left_cv + right_cv
    return Output(key, block_words, BLOCK_SIZE, 0, PARENT | flags)

def parent_cv(left_cv, right_cv, key, flags):
    return parent_output(left_cv, right_cv, key, flags).chaining_value()

def compress_subtree_to_parent_node(input, key, chunk_counter, flags):
    cv_array = [0] * OUT_LEN * 2
    output = [0] * OUT_LEN * 2
    (cv_array, num_cvs) = compress_subtree_wide(input, key, chunk_counter, flags, cv_array)
    print("cv number:", num_cvs)
    while num_cvs > 2:
        print("alrighty")
        cv_slice = cv_array[:num_cvs * OUT_LEN]
        (cv_slice, num_cvs) = compress_parents(cv_slice, key, chunk_counter, flags, output)
        cv_array[:num_cvs * OUT_LEN] = cv_slice 
    return cv_array[:2*OUT_LEN]

def compress_subtree_wide(input, key, chunk_counter, flags, cv_array):
    if len(input) <= CHUNK_LEN:
        state = ChunkState(key, chunk_counter, flags)
        state.update(input)
        return (state.output().chaining_value(), 1)

    split_ind = left_len(len(input))
    left = input[:split_ind]
    right = input[split_ind:]
    right_chunk_counter = chunk_counter + (len(left) // CHUNK_LEN)
    left_out = [0] * OUT_LEN
    right_out = [0] * OUT_LEN
    (left_out, left_num_cv) = compress_subtree_wide(left, key, chunk_counter, flags, left_out)
    (right_out, right_num_cv) = compress_subtree_wide(right, key, right_chunk_counter, flags, right_out)

    cv_array = left_out + right_out
    if left_num_cv == 1:
        print("left num 1")
        return(cv_array[:2*OUT_LEN], 2)
    else:
        num_children = left_num_cv + right_num_cv
        print("children are a lot", num_children)
        output = []
        return compress_parents(cv_array[:num_children*OUT_LEN], key, flags, output)

def compress_parents(child_chaining_values, key, flags, output):
    num_children = len(child_chaining_values) // OUT_LEN
    parents_exact = []
    for i in range(0, len(child_chaining_values), 2 * OUT_LEN):
        parents_exact.append(child_chaining_values[i:i + 2 * OUT_LEN])
    print("children values: ")
    dump_cv(child_chaining_values)
    output = [0] * (num_children // 2 * OUT_LEN)
    i = 0
    for p in parents_exact:
        output[i*OUT_LEN:(i+1)*OUT_LEN] = parent_cv(p[:OUT_LEN], p[OUT_LEN:], key, flags)
        i += 1
    print("compressed parents:")

    parents_count = len(parents_exact)
    if (parents_count * 2 * OUT_LEN) != len(child_chaining_values):
        output = output + child_chaining_values[parents_count * 2 * OUT_LEN:]
        parents_count += 1
    dump_cv(output)
    print(parents_count)
    return (output, parents_count)



def left_len (size):
    full_chunks = (size - 1) // CHUNK_LEN
    return largest_power_of_2_leq(full_chunks) * CHUNK_LEN

# Brian Kernighan’s Algorithm
def count_ones(number): 
    count = 0
    while (number): 
        number &= (number-1)  
        count += 1
    return count

def largest_power_of_2_leq(number): 
    p = int(math.log(number, 2))
    return int(pow(2, p))

class blake3_hash:
    def __init__(self, key, flags):
        self.chunk_state = ChunkState(key, 0, flags)
        self.key = key
        self.cv_stack = []
        self.cv_stack_len = 0
        self.flags = flags

    def push_cv(self, chaining_value, chunk_counter):
        self.merge_cv_stack(chunk_counter)
        self.push_stack(chaining_value)

    def push_stack(self, chaining_value):
        self.cv_stack.append(chaining_value)
        self.cv_stack_len += 1

    def pop_stack(self):
        self.cv_stack_len -= 1
        return self.cv_stack.pop()

    def merge_cv_stack(self, chunk_counter):
        post_merge_stack_len = count_ones(chunk_counter)
        while self.cv_stack_len > post_merge_stack_len:
            right_child = self.pop_stack()
            left_child = self.pop_stack()
            parent_out = parent_output(left_child, right_child, self.key, self.chunk_state.flags)
            self.push_stack(parent_out.chaining_value())

    def add_chunk_value(self, new_cv, chunk_counter):
        while chunk_counter & 1 == 0:
            new_cv = parent_cv(self.pop_stack(), new_cv, self.key, self.flags)
            chunk_counter >>= 1
        self.push_stack(new_cv)
        return new_cv

    def update(self, input):
        if self.chunk_state.len() > 0:
            want = CHUNK_LEN - self.chunk_state.len()
            take = min(want, len(input))
            self.chunk_state.update(input[:take])
            input = input[take:]

            if len(input) != 0:
                chunk_cv = self.chunk_state.output().chaining_value()
                self.push_cv(chunk_cv, self.chunk_state.chunk_counter)
                self.chunk_state = ChunkState(self.key, self.chunk_state.chunk_counter+1, self.chunk_state.flags)
            else:
                return None

        while len(input) > CHUNK_LEN:
            subtree_len = largest_power_of_2_leq(len(input))
            #print(subtree_len)
            count_so_far = self.chunk_state.chunk_counter * CHUNK_LEN

            while (subtree_len - 1)  & count_so_far != 0:
                subtree_len //= 2
            subtree_chunks = subtree_len // CHUNK_LEN
            if subtree_len <= CHUNK_LEN:
                state = ChunkState(self.key, self.chunk_state.chunk_counter, self.chunk_state.flags)
                state.update(input[:subtree_len])
                self.push_cv(state.output().chaining_value(), self.chunk_state.chunk_counter)
            else:
                cv_pair = compress_subtree_to_parent_node(input[:subtree_len], self.key, self.chunk_state.chunk_counter, self.chunk_state.flags)
                left_cv = cv_pair[:8]
                right_cv = cv_pair[8:]

                self.push_cv(left_cv, self.chunk_state.chunk_counter)
                self.push_cv(right_cv, self.chunk_state.chunk_counter + (subtree_chunks // 2))

            self.chunk_state.chunk_counter += subtree_chunks
            input = input[subtree_len:]
        
        if len(input) > 0:
            self.chunk_state.update(input)
            self.merge_cv_stack(self.chunk_state.chunk_counter)

    def final_output(self):
        if self.cv_stack_len == 0:
            return self.chunk_state.output()

        cvs_remaining = self.cv_stack_len
        if self.chunk_state.len() > 0:
            output = self.chunk_state.output()
        else:
            output = parent_output(self.cv_stack[cvs_remaining-2], self.cv_stack[cvs_remaining-1], self.key, self.chunk_state.flags)
            cvs_remaining -= 2

        while cvs_remaining > 0:
            output = parent_output(self.cv_stack[cvs_remaining - 1], output.chaining_value(), self.key, self.chunk_state.flags)
            cvs_remaining -= 1

        return output

    def finalize(self, out_block):
        output = self.final_output()
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

hasher = Blake3(mode="Simple")

expected_hash = "015094013f57a5277b59d8475c0501042c0b642e531b0a1c8f58d2163229e9690289e9409ddb1b99768eafe1623da896faf7e1114bebeadc1be30829b6f8af707d85c298f4f0ff4d9438aef948335612ae921e76d411c3a9111df62d27eaf871959ae0062b5492a0feb98ef3ed4af277f5395172dbe5c311918ea0074ce0036454f620"
expected_hash_bytes = bytes.fromhex(expected_hash)

input_len = 4096
input = []
for i in range(0, input_len):
    input.append((i % 251).to_bytes(1, byteorder="little"))
input = b''.join(input)
hash = hasher.hash(input, len(expected_hash_bytes))
print(hash.hex())
print(hash == expected_hash_bytes)
print(len([92, 158, 101, 68, 17, 227, 147, 209, 244, 190, 199, 16, 204, 213, 188, 86, 105, 171, 23, 125, 97, 10, 14, 182, 145, 252, 254, 233, 47, 180, 232, 177]))