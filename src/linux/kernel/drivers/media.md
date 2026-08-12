# V4L2 — Video4Linux2

## Overview

Video4Linux2 (V4L2) is the Linux kernel framework for video capture and output devices. It provides a unified API for webcams, TV tuners, video capture cards, and other multimedia devices. V4L2 is the second generation of the Video4Linux API (replacing the original Video4Linux), and has been the standard Linux video interface since kernel 2.6.x.

V4L2 handles video capture, video output, codec operations, and advanced media pipeline management through the media controller framework. It is the backbone of applications like video conferencing, streaming, surveillance, and video editing on Linux.

## Architecture

```
┌─────────────────────────────────────────────┐
│              Userspace Applications          │
│  (GStreamer, FFmpeg, OBS, v4l2-ctl, etc.)   │
└──────────────────┬──────────────────────────┘
                   │ /dev/videoN, /dev/v4l-subdevN
┌──────────────────┴──────────────────────────┐
│              V4L2 Core Framework             │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │  Video Dev  │  │  Media Controller    │  │
│  │  /dev/video │  │  /dev/mediaN         │  │
│  └──────┬──────┘  └──────────┬───────────┘  │
│         │                    │              │
│  ┌──────┴────────────────────┴───────────┐  │
│  │         V4L2 Subsystem                │  │
│  │  Subdev API │ MC API │ Framework API  │  │
│  └──────────────┬───────────────────────┘  │
├─────────────────┴──────────────────────────┤
│              Device Drivers                 │
│  uvcvideo │ vivid │ ivtv │ gspca │ etc.   │
└────────────────────────────────────────────┘
```

## Device Nodes

V4L2 creates several types of device nodes:

| Node | Description | Example |
|---|---|---|
| `/dev/videoN` | Video device (capture/output) | `/dev/video0` |
| `/dev/v4l-subdevN` | Sub-device (sensor, encoder) | `/dev/v4l-subdev0` |
| `/dev/mediaN` | Media controller | `/dev/media0` |
| `/dev/vbiN` | Vertical blanking interval | `/dev/vbi0` |
| `/dev/radioN` | Radio tuner | `/dev/radio0` |

### Device Discovery

```bash
# List video devices
ls /dev/video*

# Detailed device info
v4l2-ctl --list-devices

# Example output:
# Integrated Camera (usb-0000:00:14.0-1):
#         /dev/video0
#         /dev/video1
#         /dev/media0
```

## V4L2 ioctl Interface

### Core Operations

```c
#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <unistd.h>

int fd = open("/dev/video0", O_RDWR);

/* Query capabilities */
struct v4l2_capability cap;
ioctl(fd, VIDIOC_QUERYCAP, &cap);
printf("Driver: %s\n", cap.driver);
printf("Card: %s\n", cap.card);
printf("Bus: %s\n", cap.bus_info);
printf("Capabilities: 0x%x\n", cap.capabilities);
/* V4L2_CAP_VIDEO_CAPTURE, V4L2_CAP_STREAMING, etc. */
```

### Format Negotiation

```c
/* Get current format */
struct v4l2_format fmt = {0};
fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
ioctl(fd, VIDIOC_G_FMT, &fmt);
printf("Current: %ux%u, fourcc: %c%c%c%c\n",
       fmt.fmt.pix.width, fmt.fmt.pix.height,
       fmt.fmt.pix.pixelformat & 0xFF,
       (fmt.fmt.pix.pixelformat >> 8) & 0xFF,
       (fmt.fmt.pix.pixelformat >> 16) & 0xFF,
       (fmt.fmt.pix.pixelformat >> 24) & 0xFF);

/* Set desired format */
memset(&fmt, 0, sizeof(fmt));
fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
fmt.fmt.pix.width = 1920;
fmt.fmt.pix.height = 1080;
fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_YUYV;
fmt.fmt.pix.field = V4L2_FIELD_INTERLACED;
ioctl(fd, VIDIOC_S_FMT, &fmt);
/* Driver may adjust — check returned values */

/* Enumerate supported formats */
struct v4l2_fmtdesc fmtdesc = {0};
fmtdesc.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
while (ioctl(fd, VIDIOC_ENUM_FMT, &fmtdesc) == 0) {
    printf("Format: %c%c%c%c - %s\n",
           fmtdesc.pixelformat & 0xFF,
           (fmtdesc.pixelformat >> 8) & 0xFF,
           (fmtdesc.pixelformat >> 16) & 0xFF,
           (fmtdesc.pixelformat >> 24) & 0xFF,
           fmtdesc.description);
    fmtdesc.index++;
}
```

### Frame Rate

```c
/* Get current frame rate */
struct v4l2_streamparm parm = {0};
parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
ioctl(fd, VIDIOC_G_PARM, &parm);
printf("Frame rate: %u/%u fps\n",
       parm.parm.capture.timeperframe.denominator,
       parm.parm.capture.timeperframe.numerator);

/* Set frame rate */
memset(&parm, 0, sizeof(parm));
parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
parm.parm.capture.timeperframe.numerator = 1;
parm.parm.capture.timeperframe.denominator = 30;  /* 30 fps */
ioctl(fd, VIDIOC_S_PARM, &parm);
```

## Buffer Management

### Memory-Mapped Buffers (MMAP)

```c
/* Request buffers */
struct v4l2_requestbuffers req = {0};
req.count = 4;
req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
req.memory = V4L2_MEMORY_MMAP;
ioctl(fd, VIDIOC_REQBUFS, &req);

/* Map buffers */
struct buffer {
    void *start;
    size_t length;
};
struct buffer buffers[4];

for (int i = 0; i < req.count; i++) {
    struct v4l2_buffer buf = {0};
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;
    buf.index = i;
    ioctl(fd, VIDIOC_QUERYBUF, &buf);

    buffers[i].length = buf.length;
    buffers[i].start = mmap(NULL, buf.length,
                            PROT_READ | PROT_WRITE,
                            MAP_SHARED, fd, buf.m.offset);
}

/* Queue all buffers */
for (int i = 0; i < req.count; i++) {
    struct v4l2_buffer buf = {0};
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;
    buf.index = i;
    ioctl(fd, VIDIOC_QBUF, &buf);
}

/* Start streaming */
enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
ioctl(fd, VIDIOC_STREAMON, &type);

/* Capture loop */
while (1) {
    struct v4l2_buffer buf = {0};
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;
    ioctl(fd, VIDIOC_DQBUF, &buf);  /* Dequeue */

    /* Process buf.index frame */
    process_frame(buffers[buf.index].start, buf.bytesused);

    ioctl(fd, VIDIOC_QBUF, &buf);  /* Re-queue */
}

/* Stop streaming */
ioctl(fd, VIDIOC_STREAMOFF, &type);
```

### User-Pointer Buffers

```c
/* Userspace allocates buffers */
struct v4l2_requestbuffers req = {0};
req.count = 4;
req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
req.memory = V4L2_MEMORY_USERPTR;
ioctl(fd, VIDIOC_REQBUFS, &req);

/* Allocate and register user buffers */
unsigned char *user_buf = malloc(width * height * 2);
struct v4l2_buffer buf = {0};
buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
buf.memory = V4L2_MEMORY_USERPTR;
buf.m.userptr = (unsigned long)user_buf;
buf.length = width * height * 2;
ioctl(fd, VIDIOC_QBUF, &buf);
```

### DMA-BUF Buffers (Zero-Copy)

```c
/* Request DMA-BUF file descriptors */
struct v4l2_requestbuffers req = {0};
req.count = 4;
req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
req.memory = V4L2_MEMORY_DMABUF;
ioctl(fd, VIDIOC_REQBUFS, &req);

/* Export DMA-BUF FD */
struct v4l2_exportbuffer exp = {0};
exp.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
exp.index = 0;
ioctl(fd, VIDIOC_EXPBUF, &exp);
int dma_fd = exp.fd;
/* Can be passed to GPU, encoder, etc. */
```

## Controls

V4L2 controls provide runtime adjustment of device parameters:

### Standard Controls

```c
/* List all controls */
struct v4l2_queryctrl qctrl = {0};
qctrl.id = V4L2_CTRL_FLAG_NEXT_CTRL;
while (ioctl(fd, VIDIOC_QUERYCTRL, &qctrl) == 0) {
    printf("Control: %s (id=%u, min=%d, max=%d, default=%d)\n",
           qctrl.name, qctrl.id, qctrl.minimum,
           qctrl.maximum, qctrl.default_value);
    qctrl.id |= V4L2_CTRL_FLAG_NEXT_CTRL;
}

/* Get control value */
struct v4l2_control ctrl = {0};
ctrl.id = V4L2_CID_BRIGHTNESS;
ioctl(fd, VIDIOC_G_CTRL, &ctrl);
printf("Brightness: %d\n", ctrl.value);

/* Set control value */
ctrl.value = 128;
ioctl(fd, VIDIOC_S_CTRL, &ctrl);
```

### Extended Controls

```c
/* Use extended controls for more features */
struct v4l2_ext_controls ext = {0};
struct v4l2_ext_control ctrls[2];

ctrls[0].id = V4L2_CID_BRIGHTNESS;
ctrls[0].value = 128;

ctrls[1].id = V4L2_CID_CONTRAST;
ctrls[1].value = 64;

ext.controls = ctrls;
ext.count = 2;
ioctl(fd, VIDIOC_S_EXT_CTRLS, &ext);
```

### Common Controls

| Control | ID | Description |
|---|---|---|
| Brightness | `V4L2_CID_BRIGHTNESS` | Image brightness |
| Contrast | `V4L2_CID_CONTRAST` | Image contrast |
| Saturation | `V4L2_CID_SATURATION` | Color saturation |
| Hue | `V4L2_CID_HUE` | Color hue |
| White Balance | `V4L2_CID_WHITE_BALANCE_TEMPERATURE` | Color temperature |
| Exposure | `V4L2_CID_EXPOSURE_ABSOLUTE` | Exposure time |
| Focus | `V4L2_CID_FOCUS_ABSOLUTE` | Focus position |
| Gain | `V4L2_CID_GAIN` | Analog/digital gain |
| Pan/Tilt | `V4L2_CID_PAN_ABSOLUTE` | Camera orientation |

### Menu Controls

```c
/* Enumerate menu items for a control */
struct v4l2_querymenu qmenu = {0};
qmenu.id = V4L2_CID_EXPOSURE_AUTO;

while (ioctl(fd, VIDIOC_QUERYMENU, &qmenu) == 0) {
    printf("Menu item %d: %s\n", qmenu.index, qmenu.name);
    qmenu.index++;
}
```

## Media Controller

The media controller manages complex device topologies with multiple sub-devices:

### Media Controller Graph

```c
#include <linux/media.h>

int mfd = open("/dev/media0", O_RDWR);

/* Query topology */
struct media_entity_desc desc = {0};
desc.id = MEDIA_ENT_ID_FLAG_NEXT;

while (ioctl(mfd, MEDIA_IOC_ENUM_ENTITIES, &desc) == 0) {
    printf("Entity: %s (id=%u, type=0x%x, pads=%u)\n",
           desc.name, desc.id, desc.type, desc.pads);
    desc.id |= MEDIA_ENT_ID_FLAG_NEXT;
}
```

### Link Setup

```c
/* Enable a link between two entities */
struct media_link_desc link = {0};
link.source.entity = entity1_id;
link.source.index = 0;
link.sink.entity = entity2_id;
link.sink.index = 0;
link.flags = MEDIA_LNK_FL_ENABLED;
ioctl(mfd, MEDIA_IOC_SETUP_LINK, &link);
```

### Sub-device Operations

```c
/* Open sub-device */
int subdev_fd = open("/dev/v4l-subdev0", O_RDWR);

/* Get/set sub-device format */
struct v4l2_subdev_format sd_fmt = {0};
sd_fmt.which = V4L2_SUBDEV_FORMAT_ACTIVE;
sd_fmt.format.width = 1920;
sd_fmt.format.height = 1080;
sd_fmt.format.code = MEDIA_BUS_FMT_YUYV8_2X8;
ioctl(subdev_fd, VIDIOC_SUBDEV_S_FMT, &sd_fmt);
```

## Common Pixel Formats

| Format | FourCC | Description | BPP |
|---|---|---|---|
| YUYV | `YUYV` | YUV 4:2:2 packed | 16 |
| NV12 | `NV12` | YUV 4:2:2 semi-planar | 12 |
| MJPEG | `MJPG` | Motion JPEG | varies |
| RGB24 | `RGB3` | 24-bit RGB | 24 |
| H.264 | `H264` | H.264 encoded stream | varies |
| GREY | `GREY` | 8-bit grayscale | 8 |
| SRGGB10 | `RG10` | Bayer 10-bit | 10 |

## v4l2-ctl Utility

`v4l2-ctl` is the primary command-line tool for V4L2:

### Device Information

```bash
# List all devices
v4l2-ctl --list-devices

# Query device capabilities
v4l2-ctl -d /dev/video0 --all

# List supported formats
v4l2-ctl -d /dev/video0 --list-formats-ext
```

### Capture

```bash
# Capture a single frame
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=YUYV \
    --stream-mmap --stream-count=1 --stream-to=frame.raw

# Capture MJPEG video
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=MJPG \
    --stream-mmap --stream-count=30 --stream-to=video.mjpg

# Continuous capture (streaming)
v4l2-ctl -d /dev/video0 --stream-mmap --stream-to=- | ffplay -f rawvideo \
    -pixel_format yuyv422 -video_size 1920x1080 -
```

### Controls

```bash
# List all controls
v4l2-ctl -d /dev/video0 -L

# Get a control
v4l2-ctl -d /dev/video0 -C brightness

# Set a control
v4l2-ctl -d /dev/video0 -c brightness=128

# Set multiple controls
v4l2-ctl -d /dev/video0 -c brightness=128,contrast=64,saturation=100
```

### Format Information

```bash
# Current format
v4l2-ctl -d /dev/video0 --get-fmt-video

# Set format
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1280,height=720,pixelformat=MJPG

# List frame sizes for a format
v4l2-ctl -d /dev/video0 --list-framesizes=YUYV

# List frame intervals
v4l2-ctl -d /dev/video0 --list-frameintervals=width=1920,height=1080
```

## Media Controller Tools

```bash
# Show media topology
media-ctl -d /dev/media0 --print-dot | dot -Tpng > topology.png

# List entities and pads
media-ctl -d /dev/media0 -p

# Set format on a pad
media-ctl -d /dev/media0 -V '"imx219 0-0010":0 [fmt:SRGGB10_1X10/3280x2464]'

# Enable links
media-ctl -d /dev/media0 -l '"imx219 0-0010":0 -> "csi2":0 [1]'
```

## V4L2 Codec Interface

V4L2 supports hardware codec operations:

### Memory-to-Memory (M2M) Codec

```c
/* Open M2M device */
int fd = open("/dev/video10", O_RDWR);

/* Set output format (raw input) */
struct v4l2_format fmt = {0};
fmt.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
fmt.fmt.pix_mp.width = 1920;
fmt.fmt.pix_mp.height = 1080;
fmt.fmt.pix_mp.pixelformat = V4L2_PIX_FMT_NV12;
ioctl(fd, VIDIOC_S_FMT, &fmt);

/* Set capture format (encoded output) */
memset(&fmt, 0, sizeof(fmt));
fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
fmt.fmt.pix_mp.width = 1920;
fmt.fmt.pix_mp.height = 1080;
fmt.fmt.pix_mp.pixelformat = V4L2_PIX_FMT_H264;
ioctl(fd, VIDIOC_S_FMT, &fmt);
```

## Common V4L2 Drivers

| Driver | Devices | Description |
|---|---|---|
| `uvcvideo` | USB webcams | USB Video Class driver |
| `vivid` | Virtual test driver | Virtual video test device |
| `gspca` | USB webcams | Legacy USB webcam framework |
| `ivtv` | TV capture cards | Hauppauge PVR series |
| `ivtvfb` | Framebuffer | IVTV framebuffer output |
| `tw5864` | Video encoder | Techwell TW5864 H.264 encoder |
| `vim2m` | Virtual M2M | Virtual memory-to-memory codec |
| `imx-csi` | i.MX SoC | NXP i.MX camera interface |
| `sun6i-csi` | Allwinner | Allwinner camera interface |

## Userspace Libraries

### libv4l2

Provides transparent format conversion and device abstraction:

```c
#include <libv4l2.h>

/* Use v4l2_* functions instead of open/ioctl/close */
int fd = v4l2_open("/dev/video0", O_RDWR);
struct v4l2_capability cap;
v4l2_ioctl(fd, VIDIOC_QUERYCAP, &cap);
v4l2_close(fd);
```

### GStreamer

```bash
# Capture from webcam
gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink

# Capture and encode
gst-launch-1.0 v4l2src device=/dev/video0 ! video/x-raw,width=1920,height=1080 \
    ! x264enc ! mp4mux ! filesink location=output.mp4
```

### FFmpeg

```bash
# Capture from V4L2
ffmpeg -f v4l2 -video_size 1920x1080 -i /dev/video0 -frames 1 output.jpg

# Continuous capture
ffmpeg -f v4l2 -video_size 1920x1080 -framerate 30 -i /dev/video0 \
    -c:v libx264 output.mp4
```

## Troubleshooting

```bash
# Check if device is recognized
dmesg | grep -i video
dmesg | grep -i camera

# Check permissions
ls -la /dev/video*
# Add user to video group
sudo usermod -aG video $USER

# Check for exclusive access
fuser /dev/video0

# Debug with v4l2-ctl
v4l2-ctl -d /dev/video0 --all
v4l2-ctl -d /dev/video0 --list-formats-ext
```

## Further Reading

- **V4L2 API specification**: `Documentation/userspace-api/media/v4l/v4l2.rst`
- **Media controller**: `Documentation/driver-api/media/v4l2-subdev.rst`
- **V4L2 wiki**: https://linuxtv.org/wiki/
- **v4l-utils**: https://git.linuxtv.org/v4l-utils.git/
- **Source**: `drivers/media/v4l2-core/` — V4L2 core framework
- **Source**: `include/uapi/linux/videodev2.h` — V4L2 API header
- **Related**: [Media Controller API](media.md) — media pipeline management
- **Related**: [USB Video Class](usb.md) — UVC specification
- **Related**: [DMA-BUF](dma.md) — zero-copy buffer sharing
