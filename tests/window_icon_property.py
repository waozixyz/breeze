"""Sample an application's X11 icon on its test's private display."""
import ctypes
from ctypes.util import find_library
from PIL import Image


def verify_window_icon(display_name, window, source):
    x11 = ctypes.CDLL(find_library('X11'))
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x11.XInternAtom.restype = ctypes.c_ulong
    x11.XGetWindowProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_long, ctypes.c_long, ctypes.c_int, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte))]
    x11.XFree.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(display_name.encode())
    assert display, 'Cannot open the private test display'
    try:
        atom = x11.XInternAtom(display, b'_NET_WM_ICON', 0)

        def words(offset, count):
            kind, remaining, length = ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_ulong()
            bits = ctypes.c_int()
            data = ctypes.POINTER(ctypes.c_ubyte)()
            result = x11.XGetWindowProperty(display, int(window), atom, offset, count,
                0, 0, ctypes.byref(kind), ctypes.byref(bits), ctypes.byref(length),
                ctypes.byref(remaining), ctypes.byref(data))
            try:
                assert result == 0 and bits.value == 32 and length.value == count, \
                    'Native window icon is missing or incomplete'
                values = ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))
                return [values[index] & 0xffffffff for index in range(count)]
            finally:
                if data:
                    x11.XFree(data)

        with Image.open(source) as encoded:
            image = encoded.convert('RGBA')
        assert words(0, 2) == list(image.size), 'Native icon changed dimensions'
        pixels = image.load()
        samples = {(0, 0), (image.width // 2, image.height // 2),
                   (image.width - 1, image.height - 1)}
        for y in range(image.height):
            edge = next(((x, y) for x in range(image.width)
                         if 0 < pixels[x, y][3] < 255), None)
            if edge:
                samples.add(edge)
                break
        for x, y in samples:
            red, green, blue, alpha = pixels[x, y]
            expected = (alpha << 24) | (red << 16) | (green << 8) | blue
            assert words(2 + y * image.width + x, 1) == [expected], \
                f'Native icon RGBA differs at {(x, y)}'
    finally:
        x11.XCloseDisplay(display)
