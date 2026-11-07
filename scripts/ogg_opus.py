"""Ogg Opus timing and exact end trimming for the spoken clips (RFC 7845).

ffmpeg's encoder pads a clip's last frame and writes the padded length as the
stream's final granule position, so a short line gains up to ~60 ms of
near-silent codec tail. end_trim sets the final granule to the source's own
sample count, as opusenc does, so decoders stop exactly where the speech
recording ends and the clip lasts as long as its source.
"""

OPUS_RATE = 48000


def _crc_table():
    table = []
    for byte in range(256):
        value = byte << 24
        for _ in range(8):
            value = ((value << 1) ^ 0x04C11DB7) if value & 0x80000000 else value << 1
        table.append(value & 0xFFFFFFFF)
    return table


_CRC = _crc_table()


def ogg_crc(page):
    value = 0
    for byte in page:
        value = ((value << 8) & 0xFFFFFFFF) ^ _CRC[((value >> 24) ^ byte) & 0xFF]
    return value


def pages(data):
    """(offset, length, header_type, granule) of every Ogg page in data."""
    found = []
    at = 0
    while at < len(data):
        if data[at:at + 4] != b'OggS' or at + 27 > len(data):
            raise ValueError(f'no Ogg page at byte {at}')
        count = data[at + 26]
        body = 27 + count
        length = body + sum(data[at + 27:at + body])
        if at + length > len(data):
            raise ValueError('truncated Ogg page')
        granule = int.from_bytes(data[at + 6:at + 14], 'little', signed=True)
        found.append((at, length, data[at + 5], granule))
        at += length
    return found


def pre_skip(data):
    body = 27 + data[26]
    if data[:4] != b'OggS' or data[body:body + 8] != b'OpusHead':
        raise ValueError('first page is not OpusHead')
    return int.from_bytes(data[body + 10:body + 12], 'little')


def opus_frames(data):
    """Samples at 48 kHz the stream plays: final granule minus pre-skip."""
    final = pages(data)[-1][3]
    skip = pre_skip(data)
    if final <= skip:
        raise ValueError('no audio after pre-skip')
    return final - skip


def opus_seconds(data):
    return opus_frames(data) / OPUS_RATE


def end_trim(data, frames):
    """data with its final granule at pre-skip + frames (48 kHz samples).

    Only the encoder's padding in the last page may go: the stream must hold at
    least frames samples, and no earlier page may already lie past them.
    """
    found = pages(data)
    offset, length, header_type, final = found[-1]
    if not header_type & 4:
        raise ValueError('last page does not end the stream')
    target = pre_skip(data) + frames
    if final < target:
        raise ValueError(f'stream holds {final - pre_skip(data)} samples, fewer than {frames}')
    earlier = max((granule for _, _, _, granule in found[:-1] if granule >= 0), default=0)
    if earlier > target:
        raise ValueError('trimming would reach into an earlier page')
    page = bytearray(data[offset:offset + length])
    page[6:14] = target.to_bytes(8, 'little', signed=True)
    page[22:26] = bytes(4)
    page[22:26] = ogg_crc(page).to_bytes(4, 'little')
    return data[:offset] + bytes(page) + data[offset + length:]
