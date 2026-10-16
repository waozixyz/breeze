package xyz.waozi.inbe;

import android.content.ContentResolver;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageDecoder;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Build;
import android.provider.MediaStore;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

/** Android's image codecs produce a small, metadata-free private picker copy. */
final class DiaryPhotoImport {
    static final int KIND = 4;
    static final int MAX_EDGE = 1600;
    static final int MAX_BYTES = 512 * 1024;
    static final long MAX_SOURCE_BYTES = 64L * 1024 * 1024;

    static Intent pickerIntent() {
        Intent intent;
        if (Build.VERSION.SDK_INT >= 33) {
            intent = new Intent(MediaStore.ACTION_PICK_IMAGES);
        } else {
            intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
        }
        intent.setType("image/*");
        return intent;
    }

    static File copy(ContentResolver resolver, Uri uri, File directory) throws IOException {
        if (!directory.isDirectory() && !directory.mkdirs()) {
            throw new IOException("Cannot create photo import directory");
        }
        File source = File.createTempFile("diary-source-", ".tmp", directory);
        File result = null;
        boolean saved = false;
        try {
            try (InputStream input = resolver.openInputStream(uri);
                 FileOutputStream output = new FileOutputStream(source)) {
                if (input == null) {
                    throw new IOException("Cannot read selected photo");
                }
                copySource(input, output);
            }
            result = File.createTempFile("diary-", ".bin", directory);
            compress(source, result);
            saved = true;
            return result;
        } finally {
            source.delete();
            if (!saved && result != null) {
                result.delete();
            }
        }
    }

    static void copySource(InputStream input, FileOutputStream output) throws IOException {
        byte[] buffer = new byte[8192];
        long total = 0;
        int count;
        while ((count = input.read(buffer)) != -1) {
            total += count;
            if (total > MAX_SOURCE_BYTES) {
                throw new IOException("Selected photo exceeds import limit");
            }
            output.write(buffer, 0, count);
        }
    }

    static void compress(File source, File result) throws IOException {
        Bitmap bitmap = decode(source);
        try {
            Bitmap.CompressFormat format = hasTransparency(bitmap)
                    ? Bitmap.CompressFormat.PNG : Bitmap.CompressFormat.JPEG;
            while (true) {
                // Use formats understood by the existing native image host.
                // PNG preserves alpha; re-encoding drops EXIF/GPS metadata.
                try (FileOutputStream output = new FileOutputStream(result)) {
                    if (!bitmap.compress(format, 78, output)) {
                        throw new IOException("Cannot compress selected photo");
                    }
                }
                if (result.length() > 0 && result.length() <= MAX_BYTES) {
                    return;
                }
                int edge = Math.max(bitmap.getWidth(), bitmap.getHeight());
                if (edge <= 320) {
                    throw new IOException("Cannot fit selected photo in storage limit");
                }
                Bitmap smaller = scale(bitmap, Math.max(320, edge * 3 / 4));
                bitmap.recycle();
                bitmap = smaller;
            }
        } finally {
            bitmap.recycle();
        }
    }

    private static boolean hasTransparency(Bitmap bitmap) {
        if (!bitmap.hasAlpha()) {
            return false;
        }
        int[] row = new int[bitmap.getWidth()];
        for (int y = 0; y < bitmap.getHeight(); y++) {
            bitmap.getPixels(row, 0, row.length, 0, y, row.length, 1);
            for (int pixel : row) {
                if ((pixel >>> 24) != 255) {
                    return true;
                }
            }
        }
        return false;
    }

    private static Bitmap decode(File source) throws IOException {
        if (Build.VERSION.SDK_INT >= 28) {
            return ImageDecoder.decodeBitmap(ImageDecoder.createSource(source), (decoder, info, input) -> {
                int width = info.getSize().getWidth();
                int height = info.getSize().getHeight();
                int edge = Math.max(width, height);
                double ratio = Math.min(1.0, (double) MAX_EDGE / edge);
                decoder.setTargetSize(Math.max(1, (int) (width * ratio)),
                        Math.max(1, (int) (height * ratio)));
                decoder.setAllocator(ImageDecoder.ALLOCATOR_SOFTWARE);
            });
        }
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inJustDecodeBounds = true;
        BitmapFactory.decodeFile(source.getAbsolutePath(), options);
        if (options.outWidth <= 0 || options.outHeight <= 0) {
            throw new IOException("Invalid selected photo");
        }
        int edge = Math.max(options.outWidth, options.outHeight);
        options.inSampleSize = 1;
        while (edge / options.inSampleSize > MAX_EDGE) {
            options.inSampleSize *= 2;
        }
        options.inJustDecodeBounds = false;
        Bitmap bitmap = BitmapFactory.decodeFile(source.getAbsolutePath(), options);
        if (bitmap == null) {
            throw new IOException("Cannot decode selected photo");
        }
        try {
            // On older Android releases the bitmap decoder ignores JPEG EXIF.
            int orientation = new ExifInterface(source.getAbsolutePath()).getAttributeInt(
                    ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
            Matrix matrix = new Matrix();
            switch (orientation) {
                case 2:
                    matrix.setScale(-1, 1);
                    break;
                case 3:
                    matrix.setRotate(180);
                    break;
                case 4:
                    matrix.setScale(1, -1);
                    break;
                case 5:
                    matrix.setRotate(90);
                    matrix.postScale(-1, 1);
                    break;
                case 6:
                    matrix.setRotate(90);
                    break;
                case 7:
                    matrix.setRotate(270);
                    matrix.postScale(-1, 1);
                    break;
                case 8:
                    matrix.setRotate(270);
                    break;
                default:
                    return bitmap;
            }
            Bitmap oriented = Bitmap.createBitmap(bitmap, 0, 0,
                    bitmap.getWidth(), bitmap.getHeight(), matrix, true);
            if (oriented != bitmap) {
                bitmap.recycle();
            }
            return oriented;
        } catch (IOException ignored) {
            // EXIF is optional (for example PNG on older releases).
            return bitmap;
        }
    }

    private static Bitmap scale(Bitmap bitmap, int edge) {
        double ratio = (double) edge / Math.max(bitmap.getWidth(), bitmap.getHeight());
        return Bitmap.createScaledBitmap(bitmap,
                Math.max(1, (int) (bitmap.getWidth() * ratio)),
                Math.max(1, (int) (bitmap.getHeight() * ratio)), true);
    }
}
