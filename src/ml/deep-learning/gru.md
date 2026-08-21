# GRU (Gated Recurrent Unit)

The Gated Recurrent Unit (GRU) is a recurrent neural network (RNN) architecture introduced by Cho et al. in 2014 as a simpler alternative to LSTM (Long Short-Term Memory). GRUs use two gates (update and reset) instead of LSTM's three (input, forget, output), making them faster to train and deploy with comparable quality. This page covers the architecture, the comparison to LSTM, the production use cases (sequence-to-sequence, time series), and why GRUs have been largely replaced by transformers.

## The Architecture

A GRU cell has two gates:

```text
Input: x_t (current input), h_{t-1} (previous hidden state)
Output: h_t (new hidden state)

Update gate (decides how much of past to keep):
  z_t = sigmoid(W_z * x_t + U_z * h_{t-1} + b_z)

Reset gate (decides what of past to forget):
  r_t = sigmoid(W_r * x_t + U_r * h_{t-1} + b_r)

Candidate hidden state (new info to potentially add):
  h~_t = tanh(W_h * x_t + U_h * (r_t * h_{t-1}) + b_h)

Final hidden state (interpolate between past and candidate):
  h_t = (1 - z_t) * h_{t-1} + z_t * h~_t
```

The update gate `z_t` is the "memory controller": when `z_t ≈ 0`, the cell keeps the previous state; when `z_t ≈ 1`, it takes the new candidate. This is similar to LSTM's forget gate.

The reset gate `r_t` controls what part of the past to use when computing the candidate. When `r_t ≈ 0`, the candidate is computed from only the current input (ignoring the past); when `r_t ≈ 1`, the candidate uses the full past.

## Comparison to LSTM

LSTM has three gates:

```text
Input gate i_t: how much of new info to add
Forget gate f_t: how much of past to keep
Output gate o_t: how much of new state to expose
```

GRU combines input and forget into a single update gate (since `(1 - z_t) * h_{t-1}` is the "forget" and `z_t * h~_t` is the "input"), and omits the output gate (the hidden state is always the output).

| Aspect | LSTM | GRU |
|--------|------|-----|
| Gates | 3 | 2 |
| Parameters | 4× (input + candidate × 4) | 3× (input + candidate × 3) |
| Training time | Longer | ~25% shorter |
| Quality (most tasks) | Similar | Similar |
| Memory (per step) | 2 hidden states (h, c) | 1 hidden state (h) |

For most tasks, GRU matches LSTM quality with fewer parameters. For tasks that need very long-term dependencies (e.g., 1000+ step sequences), LSTM's separate cell state `c` may help.

## Production Use Cases

### Time Series Forecasting

GRU is widely used for time series forecasting (stock prices, weather, energy demand). The input is a window of past observations; the output is a forecast.

```python
import torch
import torch.nn as nn

class GRUForecaster(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers=2):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 1)
    
    def forward(self, x):
        # x shape: (batch, seq_len, input_dim)
        out, h = self.gru(x)
        return self.fc(out[:, -1, :])  # use last hidden state
```

### Sequence-to-Sequence (Translation, Summarization)

GRUs were the standard for seq2seq before transformers. The encoder encodes the input into a context vector; the decoder generates the output:

```python
class Encoder(nn.Module):
    def __init__(self, vocab_size, emb_dim, hid_dim):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, emb_dim)
        self.gru = nn.GRU(emb_dim, hid_dim, batch_first=True)
    
    def forward(self, src):
        emb = self.emb(src)
        outputs, hidden = self.gru(emb)
        return hidden  # context vector

class Decoder(nn.Module):
    def __init__(self, vocab_size, emb_dim, hid_dim):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, emb_dim)
        self.gru = nn.GRU(emb_dim + hid_dim, hid_dim, batch_first=True)
        self.fc = nn.Linear(hid_dim, vocab_size)
    
    def forward(self, tgt_token, context, hidden):
        emb = self.emb(tgt_token).unsqueeze(1)
        rnn_input = torch.cat([emb, context.unsqueeze(0)], dim=2)
        output, hidden = self.gru(rnn_input, hidden)
        return self.fc(output.squeeze(1)), hidden
```

### Speech Recognition

GRUs (and bidirectional GRUs) are used in acoustic models for speech-to-text, especially on-device where compute is limited.

### On-Device ML

GRUs are smaller and faster than transformers, making them suitable for mobile and edge devices. TensorFlow Lite supports GRU inference on Android.

## When GRU Beats Transformer

GRUs can outperform transformers in:

- **Small datasets** (transformers are data-hungry; GRUs work with <10K samples).
- **Edge devices** (GRUs have fewer parameters and FLOPs).
- **Short sequences** (<50 tokens; transformers' attention matrix is mostly zero).
- **Real-time applications** (GRU inference is ~10× faster than a comparable transformer).

## When Transformer Wins

Transformers dominate GRUs in:

- **Long sequences** (>50 tokens; transformers scale better).
- **Parallel training** (GRUs are inherently sequential; transformers can process all tokens in parallel during training).
- **Quality on large datasets** (transformers with 100M+ parameters beat GRUs on most NLP benchmarks).

The "death of RNNs" in NLP is largely a consequence of transformers' parallelism — training a 100M-parameter GRU takes ~10× longer than training a 100M-parameter transformer, even if the GRU is slightly smaller.

## The Bidirectional GRU

For tasks that need both past and future context (e.g., named entity recognition), use a bidirectional GRU:

```python
class BiGRU(nn.Module):
    def __init__(self, input_dim, hid_dim):
        super().__init__()
        self.gru = nn.GRU(input_dim, hid_dim, batch_first=True, bidirectional=True)
        self.fc = nn.Linear(hid_dim * 2, num_classes)
    
    def forward(self, x):
        out, _ = self.gru(x)
        # out shape: (batch, seq_len, 2*hid_dim) — concatenation of forward and backward
        return self.fc(out)
```

The forward GRU processes the sequence left-to-right; the backward processes right-to-left. The outputs are concatenated, giving each position information about both past and future.

## Common Pitfalls

1. **Forgetting that GRUs require sequential processing.** Unlike transformers, GRUs can't be parallelized across the time dimension. Training is much slower.

2. **Forgetting to initialize the hidden state.** The hidden state `h_0` defaults to zero, which is fine for most tasks but can be improved with learned initialization.

3. **Forgetting that GRUs suffer from vanishing gradients on very long sequences.** Despite the gating, sequences >500 steps can still see gradient decay. Use attention or transformers for very long sequences.

4. **Forgetting that bidirectional GRUs need padding for batches.** Variable-length sequences in a batch must be padded to the same length; the GRU processes the padding too. Use `pack_padded_sequence` to skip the padding.

5. **Forgetting that GRUs need careful learning rate.** Too high → gradient explosion; too low → slow training. Clip gradients to a max norm (e.g., 5.0).

6. **Forgetting that GRUs are stateful across batches.** If the model state is preserved across batches (e.g., for streaming inference), the hidden state must be carefully managed. PyTorch's `nn.GRU` supports this via the `h_0` argument.

## References

- Cho et al., "[Learning Phrase Representations using RNN Encoder-Decoder for Statistical Machine Translation](https://arxiv.org/abs/1406.1078)" (EMNLP 2014) — GRU paper
- Chung et al., "[Empirical Evaluation of Gated Recurrent Neural Networks on Sequence Modeling](https://arxiv.org/abs/1412.3555)" (2014) — GRU vs LSTM comparison
- [PyTorch GRU documentation](https://pytorch.org/docs/stable/generated/torch.nn.GRU.html)
- [TensorFlow GRU documentation](https://www.tensorflow.org/api_docs/python/tf/keras/layers/GRU)
- Hochreiter & Schmidhuber, "[Long Short-Term Memory](https://www.bioinf.jku.at/publications/older/2604.pdf)" (Neural Computation 1997) — LSTM paper
- Vaswani et al., "[Attention Is All You Need](https://arxiv.org/abs/1706.03762)" (NeurIPS 2017) — transformers replace RNNs
- [The Unreasonable Effectiveness of Recurrent Neural Networks](https://karpathy.github.io/2015/05/21/rnn-effectiveness/) (Andrej Karpathy blog)
