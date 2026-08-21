# WebCodecs

WebCodecs is a low-level browser API for encoding and decoding audio and video. It exposes the same hardware-accelerated codec machinery that `<video>`, MediaRecorder, and WebRTC use internally, but as individual `VideoEncoder`, `VideoDecoder`, `AudioEncoder`, `AudioDecoder`, `ImageDecoder`, and `ImageEncoder` objects. The point is to let applications manage the encode/decode pipeline directly — control latency, drop frames, choose codecs, and process raw frames without going through opaque container formats like MP4 or WebM.

Shipped in Chrome 94 (Sept 2021). Safari 16.4 has partial support (VideoDecoder/VideoEncoder); Firefox is still behind a flag as of 2024.

## Why a New API

Before WebCodecs, the only browser-side options for media were:

| API | What it does | Limitation |
|-----|--------------|------------|
| `<video>` / `<audio>` | Play containerized media | No access to individual frames |
| `MediaRecorder` | Encode a `MediaStream` into opaque blobs | High latency, no per-frame control, only the system's preferred codec |
| `CanvasCaptureStream` + `MediaRecorder` | Encode canvas content | Opaque output, no control over keyframes |
| WebRTC | Encode/decode for P2P | Opaque; for streaming only |

None of these expose **frames** to JavaScript. Want to do real-time computer vision on a webcam feed? You'd capture to `<video>`, draw to canvas, and `getImageData` — three copies and a 100 ms latency floor. Want to encode a 4K H.264 stream from canvas animation with <50 ms latency? You couldn't.

WebCodecs exposes `VideoFrame` (a `MediaStreamTrackGenerator`-compatible buffer that may be GPU-resident) directly to JS. You can pass it to a `VideoEncoder` and get encoded `EncodedVideoChunk` objects back in microseconds.

## The Codec String

Every WebCodecs operation needs a `codec` string identifying the exact bitstream profile. The format follows the W3C codec registry and is largely inherited from MP4 box format `avc1.PPCCLL`:

| Codec | String example | Notes |
|-------|-----------------|-------|
| H.264 (AVC) | `avc1.42001f` | Baseline profile, level 3.1 |
| H.264 (AVC) | `avc1.640028` | High profile, level 4.0 |
| VP9 | `vp09.00.10.08` | Profile 0, level 1.0, bit depth 8 |
| AV1 | `av01.0.04M.08` | Main profile, level 4, 8-bit |
| HEVC | `hvc1.1.4.L93.B0` | Main profile, level 3.1 |
| Opus (audio) | `opus` | Single string for any Opus variant |
| AAC (audio) | `mp4a.40.2` | Low Complexity AAC-LC |

The codec string encodes profile, level, and constraints — critical because the hardware decoder may only support a subset. `isConfigSupported()` returns whether the user agent can decode that codec:

```js
const support = await VideoDecoder.isConfigSupported({
  codec: 'avc1.42001f',
  codedWidth: 1920,
  codedHeight: 1080,
  hardwareAcceleration: 'prefer-hardware',
});
if (!support.supported) {
  // fall back to vp8 or software avc1
}
```

## The Frame and Chunk Model

The core data types are:

```
+------------------+       encode       +--------------------+
| VideoFrame       |   ----------------> | EncodedVideoChunk  |
| (raw, planar)    |                     | (NAL packet,      |
| GPU or CPU mem   | <----------------   |  avc1, ivf, etc.) |
+------------------+       decode       +--------------------+
```

### VideoFrame

A `VideoFrame` is a raw, decoded frame. It can be constructed from many sources:

```js
// From a canvas.
const frame = new VideoFrame(canvas, { timestamp: performance.now() });

// From raw RGBA bytes (typed array).
const buffer = new Uint8Array(width * height * 4);
const frame = new VideoFrame(buffer, {
  format: 'RGBA',  // or 'RGBX', 'BGRA', 'I420', 'NV12', 'YUV420P'
  codedWidth: width,
  codedHeight: height,
  timestamp: 0,
});

// From another frame (cropping).
const cropped = new VideoFrame(frame, {
  visibleRect: { x: 10, y: 10, width: 100, height: 100 },
  timestamp: frame.timestamp,
});

// From a video element's track.
const track = videoElement.captureStream().getVideoTracks()[0];
const processor = new VideoTrackProcessor(track);
// Async iteration of frames.
```

The `format` matters: `'I420'` (planar YUV 4:2:0) is what most codecs actually encode, while `'RGBA'` requires a CPU-side conversion. Whenever possible, request the format the hardware encoder prefers.

Each frame has a `timestamp` (in microseconds) and optional `duration`. Encoders order by timestamp; decoders return frames in display order (after reordering).

### EncodedVideoChunk

An `EncodedVideoChunk` is a compressed slice or NAL unit. Its `type` is either `"key"` (I-frame, decodable standalone) or `"delta"` (P/B-frame, requires previous frames).

```js
new EncodedVideoChunk({
  type: 'key',                       // or 'delta'
  timestamp: 0,                      // microseconds
  duration: 33333,                   // microseconds (one frame at 30 fps)
  data: naluBuffer,                  // ArrayBuffer of the bitstream bytes
});
```

## VideoEncoder

The `VideoEncoder` is a stateful machine. You `configure()` it once, then call `encode(frame)` repeatedly. The output is delivered to the `output` callback:

```
        +-----------+                  +-----------+
        |  Config   |  configure()    |           |
        +-----------+   ----------->   |    HOT    |
                                       |  ENCODE  |  chunk -> output callback
        +-----------+  encode()        |          |
        | VideoFrame|   ----------->   |          |
        +-----------+                  +----------+
                          error callback ^
```

### A Complete Encode Loop

```js
const encoder = new VideoEncoder({
  output: (chunk, metadata) => {
    if (metadata.decoderConfig) {
      // Sent once at the start; required to initialize the decoder.
      // Contains extradata (SPS/PPS for avc1, OBU sequence header for av1).
      console.log('decoder config', metadata.decoderConfig);
    }
    // Send chunk over network or append to MP4 muxer.
    sendChunk(chunk);
  },
  error: (e) => console.error('encode error', e),
});

await encoder.configure({
  codec: 'avc1.42001f',
  width: 1280,
  height: 720,
  bitrate: 2_000_000,           // 2 Mbps
  framerate: 30,
  keyFrameInterval: 60,         // force I-frame every 60 frames
  latencyMode: 'realtime',      // or 'quality'
  hardwareAcceleration: 'prefer-hardware',
});

// Encode a stream of frames.
const trackGenerator = new VideoTrackGenerator({ fps: 30 });
trackGenerator.writable.getWriter().write(frame);

for (const frame of frames) {
  encoder.encode(frame, { keyFrame: false });
  frame.close();  // release the GPU/CPU buffer
}

await encoder.flush();
encoder.close();
```

Key points:

- `frame.close()` is mandatory. Frames hold non-trivial memory (often GPU-resident); not closing them leaks.
- `latencyMode: 'realtime'` tells the encoder to use the smallest possible look-ahead buffer — useful for cloud gaming (<10 ms target).
- `bitrate` may be a fixed value or set via `BitrateMode` (`'constant'` or `'variable'`).
- `hardwareAcceleration: 'prefer-hardware'` is a hint; the encoder may still use software.

## VideoDecoder

```js
const decoder = new VideoDecoder({
  output: (frame) => {
    // Draw the frame on a canvas, OR pass to another encoder, OR
    // pass to a WebGL/WebGPU texture via `copyToTexture`.
    drawFrame(frame);
    frame.close();
  },
  error: (e) => console.error('decode error', e),
});

await decoder.configure({
  codec: 'avc1.42001f',
  codedWidth: 1280,
  codedHeight: 720,
  hardwareAcceleration: 'prefer-hardware',
});

// Feed encoded chunks.
for (const chunk of receivedChunks) {
  decoder.decode(chunk);
}
await decoder.flush();
decoder.close();
```

The decoder asynchronously reorders B-frames; the output callback fires in display order, not decode order. If you need timing, `frame.timestamp` carries the presentation time.

## AudioEncoder / AudioDecoder

Same shape, different data types — `AudioData` (interleaved or planar PCM) and `EncodedAudioChunk`:

```js
const aenc = new AudioEncoder({
  output: (chunk, meta) => sendAudio(chunk),
  error: (e) => console.error(e),
});
await aenc.configure({
  codec: 'opus',
  sampleRate: 48000,
  numberOfChannels: 2,
  bitrate: 128_000,
});

// Each AudioData holds one or more frames of PCM samples.
const data = new AudioData({
  format: 'f32-planar',
  sampleRate: 48000,
  numberOfFrames: 960,    // 20 ms at 48 kHz
  numberOfChannels: 2,
  data: pcmBuffer,
  timestamp: 0,
});
aenc.encode(data);
data.close();
```

Opus is the typical choice (low latency, royalty-free). AAC is supported for compatibility; FLAC and ALAC for archival.

## Hardware Acceleration

Modern systems use dedicated silicon (Intel QSV, NVIDIA NVENC, AMD VCE, Apple Silicon media engines) for encode/decode. WebCodecs exposes this through the `hardwareAcceleration` configuration option, which has three modes:

- `'no-preference'` — default; browser picks.
- `'prefer-hardware'` — use hardware if available.
- `'prefer-software'` — use software (useful when hardware is buggy or you need a codec the hardware doesn't support).

Hardware encoders may have constraints: max 8K resolution, only certain profiles of AV1, fixed bitrate ceiling. Always check `isConfigSupported()` first.

For the highest throughput (e.g., 4 simultaneous 4K60 encodes for cloud gaming), you need hardware; software encoders max out at maybe one 1080p60 stream on a typical CPU.

## Comparison to MediaRecorder

| Aspect | MediaRecorder | WebCodecs |
|-------|---------------|-----------|
| Output format | Opaque container blobs (WebM, MP4) | Raw encoded chunks |
| Latency | 100-1000 ms (buffering, muxer) | <10 ms per frame |
| Codec choice | Limited (browser's preference) | Application picks |
| Frame-level control | None | Full (timestamps, keyframes, drops) |
| Hardware encoder | Maybe | Yes (with `prefer-hardware`) |
| Stream source | MediaStream (canvas, webcam) | VideoFrame from any source |
| Where it fits | Recording UI demos, screen captures | Cloud gaming, video processing, WebRTC alternatives |

The most important difference is **latency**. MediaRecorder buffers frames in a muxer and produces blobs at intervals; you can't observe or control individual frames. WebCodecs emits a chunk per encoded frame, with microsecond timestamps. For cloud gaming (GeForce NOW, Stadia-style services), WebCodecs + WebTransport is the canonical stack.

## Real-World Use Cases

### Cloud Gaming

The server renders a frame, encodes to H.264 at the GPU's hardware encoder, ships NALUs over WebTransport datagrams (unreliable — late packets are useless), and the browser decodes them and composites to a canvas. End-to-end latency: ~30 ms on a good connection. This is what GeForce NOW uses (although they ship a custom client; web clients use WebCodecs too).

### Webcam + Computer Vision Pipeline

```js
const stream = await navigator.mediaDevices.getUserMedia({ video: true });
const track = stream.getVideoTracks()[0];
const processor = new MediaStreamTrackProcessor(track);
const reader = processor.readable.getReader();

while (true) {
  const { value: frame, done } = await reader.read();
  if (done) break;
  // Pass to WebGL texture or tf.browser.fromPixels.
  // No intermediate canvas, no getImageData copy.
  runInference(frame);
  frame.close();
}
```

Before WebCodecs, the same flow needed `<video>` → `canvas.drawImage` → `getImageData` — three GPU→CPU copies, plus a trip through the layout pipeline. WebCodecs hands you a `VideoFrame` you can pass directly to `WebGLTexture` via `texImage2D` or to a `WebGPUTexture` via `copyExternalImageToTexture`.

### Video Editing in the Browser

Decode an MP4 to frames, apply filters (using WebGL/WebGPU), re-encode to AV1 for distribution. WebCodecs handles the decode/encode; the muxer (e.g., `mp4box.js`) handles the container.

## Pitfalls

1. **Forgetting to `close()` frames.** Each `VideoFrame` and `AudioData` holds GPU or CPU memory; not closing leaks resources fast (a 4K YUV420 frame is ~6 MB; 30 fps = 180 MB/s of leaked memory).
2. **Not handling B-frames.** Decoders return frames in display order, not decode order. If you push chunks into another encoder assuming order, you'll get garbled output.
3. **Extradata is mandatory.** The first `output` callback carries `metadata.decoderConfig` (SPS/PPS for H.264). You MUST send this to the decoder before any chunk — otherwise decode fails.
4. **Backpressure.** `encode()` is async but the queue is bounded. If you don't await `encoder.encodeQueueSize` or call `flush()`, you'll OOM. Use the queue size as a backpressure signal — if it's >4, slow down.
5. **Codec string typos.** `avc1.42E01F` (capital E) works on some platforms; `avc1.42001f` is canonical. Always test with `isConfigSupported()`.

## Interview Questions

**Q1: Why does WebCodecs exist if we already have MediaRecorder?**
A: MediaRecorder produces opaque container blobs with high latency (100 ms+ buffering). WebCodecs exposes individual `EncodedVideoChunk` objects with per-frame control over keyframes, bitrate, latency mode, and codec choice. For cloud gaming, real-time video processing, or any low-latency use case, MediaRecorder is unusable — you can't observe frames as they're encoded.

**Q2: What is a `VideoFrame` and why does it have a `close()` method?**
A: A `VideoFrame` is a decoded raw frame — possibly GPU-resident. It holds significant memory (6 MB for 4K YUV420). `close()` releases the underlying buffer back to the encoder/decoder pool. Not calling it leaks; the GC won't save you because the underlying resource is native.

**Q3: What's the difference between `prefer-hardware` and `prefer-software` acceleration modes?**
A: `prefer-hardware` asks the browser to use the system's hardware encoder (NVENC, QSV, Apple media engine) — higher throughput, lower CPU usage, but possibly fewer codecs and lower quality at low bitrates. `prefer-software` forces software encoding — useful when hardware has a bug or you need a codec the hardware doesn't support (e.g., some AV1 profiles on older GPUs).

**Q4: How does WebCodecs fit with WebTransport for cloud gaming?**
A: Server renders → hardware-encodes to H.264 NALUs → ships them as WebTransport datagrams (unreliable — late packets are useless) → browser `VideoDecoder` decodes → `VideoFrame` is drawn to canvas or WebGPU texture. End-to-end latency can hit ~30 ms; MediaRecorder + WebSocket would be 200+ ms.

**Q5: What is `decoderConfig` metadata in the encoder output callback?**
A: The first call to the encoder's `output` callback carries `metadata.decoderConfig` containing codec-specific extradata (SPS/PPS for H.264, sequence header OBU for AV1). This MUST be sent to the decoder before any `EncodedVideoChunk`, or decoding fails. It describes the decoder's initialization state — frame dimensions, profile, color space.

## References

- [W3C WebCodecs Specification](https://www.w3.org/TR/webcodecs/)
- [MDN: WebCodecs API](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API)
- [Chrome Developers: WebCodecs](https://developer.chrome.com/docs/capabilities/webcodecs)
- [WebCodecs Samples Repository](https://w3c.github.io/webcodecs/samples/)
- [W3C VideoFrame reference](https://w3c.github.io/webcodecs/#videoframe-interface)
- [W3C codec registry](https://www.w3.org/TR/webcodecs-codec-registry/)
- [Chromium blog: WebCodecs now in Chrome 94](https://developer.chrome.com/blog/webcodecs-now-shipped)
- [Can I Use: WebCodecs](https://caniuse.com/webcodecs)
