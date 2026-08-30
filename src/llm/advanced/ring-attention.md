# Ring Attention: Sequence Parallelism for Long Context

Data, tensor, and pipeline parallelism all shard the *model*; the sequence
dimension stays whole on every device. Ring Attention (Liu, Zaharia, Abbeel,
2023) removes that ceiling: it splits the sequence across devices and
circulates key/value blocks around a device ring, so blockwise attention --
the same tiling Flash Attention uses inside one GPU
([Flash Attention](./flash-attention.md)) -- runs on one block while the
next is in flight over the network: exact attention over 128K-1M+ token
sequences, with per-device memory shrinking as 1/P in the ring size.

## Why Long Context Breaks Single-Device Training

The standard playbook shards parameters: tensor parallelism splits weight
matrices (Megatron-style), pipeline parallelism assigns layers to stages,
and ZeRO/FSDP data parallelism shards optimizer state, gradients, and
parameters across replicas ([model parallelism](./distributed/model-parallelism.md),
[ring allreduce](./distributed/ring-allreduce.md)). None touch the sequence
axis: every device still materializes activations for all N tokens, and the
unfused attention score matrix grows as N^2.

Run the numbers for a 70B-class model (hidden size h = 8192, 80 layers, bf16):

```text
KV per token per layer : 2 (K and V) x 8192 x 2 bytes      =  32 KB
KV, full sequence, one layer, N = 128K tokens              =   4 GiB
KV, 80 layers, N = 128K                                    = 320 GiB
KV, 80 layers, N = 1M                                      = 2.5 TiB
```

No 80 GB HBM holds 320 GiB, and activation checkpointing only trades compute
for memory without changing the asymptotics. Splitting the sequence across
devices is the only axis left.

```text
| Approach             | Split axis           | Sequence state per device | Practical long-context ceiling |
|----------------------|----------------------|---------------------------|--------------------------------|
| Data + ZeRO / FSDP   | batch (params split) | all N tokens              | ~32K tokens                    |
| Tensor parallel      | weight matrices      | all N tokens              | ~32K tokens                    |
| Pipeline parallel    | layers               | all N tokens              | ~32K tokens                    |
| Sequence parallel    | tokens               | N / P tokens              | 128K - 1M+ tokens              |
```
(Ceilings are order-of-magnitude; they depend on model width and layer count.)

## Ring Attention: Compute While You Communicate

Partition the sequence into P blocks of B tokens. Device i owns query block
Q_i and KV block (K_i, V_i) for its slice, then repeats for P steps:
(1) compute blockwise attention of Q_i against the KV block *currently
resident* -- online-softmax tiling as in Flash Attention, so partial outputs
merge correctly block by block; (2) forward the resident KV block to the
right neighbor, receive the next from the left. After P steps every device
has attended its queries against every KV block.

```text
                  +----------+
             .--->| device 0 |----.      step k: device i attends Q_i vs
             |    +----------+    |      KV block (i - k) mod P, then
             |                    v      forwards it: i -> (i+1) mod P
      +----------+          +----------+
      | device 3 |          | device 1 |
      +----------+          +----------+
             ^                    |
             '----| device 2 |<---'
                  +----------+
      Device 0's view over 4 steps:  KV[0] -> KV[3] -> KV[2] -> KV[1]
```

Each device permanently holds only its own KV shard -- 2 x (N/P) x h x 2
bytes per layer, linear in N/P; the other P-1 shards are streams passing
through, one block at a time, and attention state stays O(B x h), never N x N.

**The pipelining insight.** Blockwise attention needs only the *current* KV
block, so transferring the *next* block is independent work that overlaps
compute. Let c = ticks per block-attention, m = ticks per hop. If m <= c,
every transfer hides under compute and the ring finishes in P x c ticks
instead of P x (c + m); steady-state throughput is one block-attention per
max(c, m) ticks.

## The Causal-Mask Problem: Striped Attention

Causal masking breaks the balance. With contiguous blocks, device 0's
queries see only KV block 0 (the rest is masked) while device P-1's queries
see all P blocks, so the last device does about P times the attention work
of the first -- and a ring runs at its slowest member.

Striped Attention (Brandon et al., 2023) fixes this by changing the
*assignment*, not the algorithm: distribute query rows round-robin
(row r -> device r mod P) so each device's queries span the whole sequence,
balancing unmasked KV-block visits to ~1:1 (shown below). It also removes
the padding waste the original ring paper handles by padding unequal shards.
A third variant, *zigzag* ring attention (ring-flash-attention
implementations), gives each device two half-blocks placed symmetrically
near the start and end of the sequence -- balanced without row-level scatter.

## The Variant Landscape: Head-Sharding vs Ring-Sharding

Ring Attention grew out of the Blockwise Parallel Transformer (BPT) framework
from the same paper: blockwise computation for attention, the feedforward
network, and layer norm, with a host-offload variant that spills KV blocks
to CPU memory. Production systems chose different points in the design space:

- **Megatron sequence parallelism** (Korthikanti et al., 2022) predates the
  ring: it splits only sequence-invariant regions (LayerNorm, dropout) with
  all-gather/reduce-scatter around tensor-parallel regions; attention stays
  head-sharded ([Megatron-style parallelism](./distributed/megatron.md)).
- **DeepSpeed-Ulysses** scatters the sequence with all-to-all before
  attention and gathers heads: each device holds N/P tokens but all heads
  during the attention core, then all-to-alls back.
- **LoongTrain** combines the two: Ulysses-style head sharding on top of
  ring-style context sharding, plus a double-ring (two counter-rotating rings
  over different link tiers) to cut per-hop latency on multi-node clusters.

```text
| System            | Sequence/KV placement     | Per-layer comm             | Causal-mask balance      | Sweet spot                    |
|-------------------|---------------------------|----------------------------|--------------------------|-------------------------------|
| Ring / BPT        | ring of KV shards         | P2P send/recv (ring)       | poor; fix: striped/zigzag| very long seq, few devices    |
| Megatron-SP       | full seq; heads split     | all-gather + reduce-scatter| good (inherits TP)       | paired with tensor parallel   |
| DeepSpeed-Ulysses | full seq; heads split     | all-to-all (2x per layer)  | good                     | moderate seq, many devices    |
| LoongTrain        | hybrid: heads x ring      | all-to-all + ring P2P      | good (double-ring)       | 128K+ across multi-node       |
```

The structural difference: ring-based schemes shard attention along the
*sequence* axis of K/V (memory scales with the sequence), head-based schemes
shard along the *head* axis (comm efficiency scales with the all-to-all),
and hybrids pay each currency where it is cheap.

## Cost Analysis: When the Ring Wins

Communication volume, per device per layer: the ring sends its KV shard
P-1 times, i.e. (P-1)/P x full-sequence KV bytes -- the whole KV stream
crosses each device once, independent of P to first order. Head-sharding's
all-to-all moves less data as P grows, but each device holds the full
sequence around the all-to-all, so it never relieves sequence-state memory
outside the attention core. Ring keeps sequence state at N/P everywhere.

Overlap decides the rest. With the demo's tick model, overlapped ring time
is P x max(c, m) vs P x (c + m) serialized. When c >> m -- long sequences
with fat blocks, or a slow network -- overlap hides the network and adding
devices shrinks memory at nearly no time cost. When m >> c -- short
sequences, tiny blocks -- the ring runs at network speed and head-sharding's
fewer, larger all-to-all transfers use the fabric better.

So: few devices and very long sequences favor the ring; many devices and
short sequences favor head-sharding. Double-ring schemes exist to keep c/m
favorable on clusters with fast intra-node and slow inter-node links. The
same overlap accounting governs ring allreduce on HPC fabric
([collective communication](../../hpc/collective-communication.md)).

## Worked Demo: A 4-Device Ring in Discrete Ticks

The simulation models one attention layer on a P=4 ring. Part 1 prints
device 0's per-step timeline (compute interval, KV-transfer interval) for
overlapped vs non-overlapped schedules. Part 2 counts causal-mask work per
device (unmasked KV-block visits) for contiguous vs striped assignment.

```python
"""Ring attention on a 4-device ring: discrete-tick simulation.

Part 1: overlapped vs non-overlapped ring schedules, per-step timeline.
Part 2: causal-mask workload per device, contiguous vs striped assignment.
Model: P devices, P equal KV blocks; c ticks per block-attention,
m ticks per hop. One sequence, one layer, one head.
"""
P, C, M = 4, 3, 1      # devices, ticks per block-attention, ticks per hop

def ring_timeline(c, m, p, overlap):
    """Device 0's schedule. Return (per-step intervals, total ticks)."""
    steps, t = [], 0
    for k in range(p):
        if overlap:
            comp, tx = (t, t + c), (t, t + m, (k + 1) % p)
            t += max(c, m)                       # compute gates the ring
        else:
            comp, tx = (t, t + c), (t + c, t + c + m, (k + 1) % p)
            t += c + m                           # send AFTER compute
        steps.append((k, comp, tx))
    return steps, t

for overlap in (False, True):
    mode = "overlapped" if overlap else "non-overlapped"
    steps, total = ring_timeline(C, M, P, overlap)
    print(f"{mode} ring (c={C}, m={M}):")
    for k, comp, tx in steps:
        print(f"  step {k}: compute ticks {comp[0]:2d}-{comp[1]:2d} | "
              f"send KV[{tx[2]}] ticks {tx[0]:2d}-{tx[1]:2d}")
    print(f"  total: {total} ticks")

# Part 2: causal-mask load balance, work measured in KV-block visits
B = 8                          # query rows per block
N = P * B                      # total query rows in the sequence

def device_work(assignment):
    work = [0] * P
    for row, dev in enumerate(assignment):
        work[dev] += row // B + 1              # blocks 0..row//B unmasked
    return work

contiguous = [i // B for i in range(N)]        # device i owns rows i*B..(i+1)*B-1
striped = [i % P for i in range(N)]            # round-robin rows across devices
for name, a in (("contiguous", contiguous), ("striped   ", striped)):
    w = device_work(a)
    print(f"{name}: work per device = {w}  max/min = {max(w)/min(w):.2f}x  "
          f"total = {sum(w)}")
```

Output (verbatim run of the script above):

```text
non-overlapped ring (c=3, m=1):
  step 0: compute ticks  0- 3 | send KV[1] ticks  3- 4
  step 1: compute ticks  4- 7 | send KV[2] ticks  7- 8
  step 2: compute ticks  8-11 | send KV[3] ticks 11-12
  step 3: compute ticks 12-15 | send KV[0] ticks 15-16
  total: 16 ticks
overlapped ring (c=3, m=1):
  step 0: compute ticks  0- 3 | send KV[1] ticks  0- 1
  step 1: compute ticks  3- 6 | send KV[2] ticks  3- 4
  step 2: compute ticks  6- 9 | send KV[3] ticks  6- 7
  step 3: compute ticks  9-12 | send KV[0] ticks  9-10
  total: 12 ticks
contiguous: work per device = [8, 16, 24, 32]  max/min = 4.00x  total = 80
striped   : work per device = [20, 20, 20, 20]  max/min = 1.00x  total = 80
```

Reading it: overlap cuts the ring from 16 to 12 ticks (the saving reaches
the full P x m when blocks are compute-heavy), and contiguous assignment
makes device 3 do 4x device 0's work while striping gives every device 20 of
the 80 block-visits. Real ring attention adds online-softmax bookkeeping, a
backward pass whose gradients traverse the same ring, and a real fabric.

## Common Pitfalls

1. **Conflating the two "sequence parallelisms."** Megatron-SP (2022) splits
   sequence-parallel regions around tensor parallelism; ring attention (2023)
   shards the sequence itself. Both are called "sequence parallelism" --
   check the comm primitive (all-gather vs ring send/recv) to tell them apart.
2. **Deploying plain ring attention with causal masks.** The last device
   becomes the straggler; wall time is set by the most-loaded member. Use
   striped or zigzag assignment.
3. **Assuming overlap is free.** If per-hop transfer time exceeds per-block
   compute, the ring runs at network speed and adding devices buys memory,
   not time. Measure c and m on your fabric before committing.
4. **Expecting bit-identical outputs.** Online softmax merges blocks in ring
   order, so results are mathematically exact but numerically differ from
   single-device attention (same tolerance situation as Flash Attention).

At inference time the same long-context pressure reappears as KV-cache
pressure and prefill latency ([Inference Systems](./inference-systems.md));
ring-style sharding shows up in long-context serving stacks too.

## References

- Hao Liu, Matei Zaharia, Pieter Abbeel, "[Ring Attention with Blockwise Transformers for Near-Infinite Context](https://arxiv.org/abs/2310.01889)" (2023)
- William Brandon, Mayank Mishra, Aniruddha Nrusimha, Rameswar Panda, Jonathan Ragan-Kelley, "[Striped Attention: Faster Ring Attention for Causal Transformers](https://arxiv.org/abs/2311.09431)" (2023)
- Vijay Korthikanti et al., "[Reducing Activation Recomputation in Large Transformer Models](https://arxiv.org/abs/2205.05198)" (Megatron sequence parallelism, 2022)
- [DeepSpeed-Ulysses: Training Long-Sequence Transformer Models tutorial](https://www.deepspeed.ai/tutorials/ds-sequence/) (DeepSpeed documentation)
- "[LoongTrain: Efficient Training of Long-Sequence LLMs with Head-Context Parallelism](https://arxiv.org/abs/2406.18485)" (2024)
- Tri Dao et al., "[FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135)" (NeurIPS 2022) -- see also [Flash Attention](./flash-attention.md)
- [ring-flash-attention](https://github.com/zhuzilin/ring-flash-attention) (reference implementation incl. zigzag variant)
