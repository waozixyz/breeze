package xyz.waozi.inbe;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.ExecutorService;

/** Bounded platform HTTP effects. Request policy and authentication live in Zi. */
final class HttpTransport {
    private static final int LIMIT = 16 * 1024 * 1024;
    private final ConcurrentHashMap<Integer, Transfer> transfers = new ConcurrentHashMap<>();
    private final ExecutorService workers = Executors.newFixedThreadPool(3);
    private final ScheduledExecutorService timers = Executors.newSingleThreadScheduledExecutor();
    private int next = 1;
    private boolean closed;

    private static final class Transfer {
        final String method;
        final URL url;
        final int capacity;
        final int timeout;
        final Map<String, String> headers = new LinkedHashMap<>();
        volatile HttpURLConnection connection;
        volatile Future<?> worker;
        volatile ScheduledFuture<?> timer;
        volatile boolean cancelled;
        boolean sent;
        int state = -1;
        byte[] response;

        Transfer(String method, URL url, int capacity, int timeout) {
            this.method = method;
            this.url = url;
            this.capacity = capacity;
            this.timeout = timeout;
        }
    }

    private static String text(byte[] bytes) throws Exception {
        return StandardCharsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(ByteBuffer.wrap(bytes)).toString();
    }

    synchronized int create(byte[] methodBytes, byte[] urlBytes, int capacity, int timeout) {
        if (closed || methodBytes == null || urlBytes == null || methodBytes.length < 1 ||
            methodBytes.length > 31 || urlBytes.length < 1 || urlBytes.length >= 2048 ||
            capacity < 1 || capacity > LIMIT || timeout < 1 || timeout > 900000 ||
            transfers.size() >= 8) {
            return 0;
        }
        try {
            String method = text(methodBytes);
            URL url = new URL(text(urlBytes));
            if (!method.matches("[A-Za-z-]+") ||
                !("https".equals(url.getProtocol()) || "http".equals(url.getProtocol())) ||
                url.getUserInfo() != null || url.getHost().isEmpty()) {
                return 0;
            }
            while (transfers.containsKey(next)) {
                next = next == Integer.MAX_VALUE ? 1 : next + 1;
            }
            int id = next;
            next = next == Integer.MAX_VALUE ? 1 : next + 1;
            Transfer transfer = new Transfer(method, url, capacity, timeout);
            transfers.put(id, transfer);
            transfer.timer = timers.schedule(() -> expire(id, transfer), timeout,
                TimeUnit.MILLISECONDS);
            return id;
        } catch (Exception error) {
            return 0;
        }
    }

    boolean header(int id, byte[] nameBytes, byte[] valueBytes) {
        Transfer transfer = transfers.get(id);
        if (transfer == null || nameBytes == null || valueBytes == null ||
            nameBytes.length < 1 || nameBytes.length > 128 || valueBytes.length > 8192) {
            return false;
        }
        try {
            String name = text(nameBytes);
            String value = text(valueBytes);
            if (!name.matches("[!#$%&'*+.^_`|~0-9A-Za-z-]+") ||
                value.indexOf('\r') >= 0 || value.indexOf('\n') >= 0 || value.indexOf('\0') >= 0) {
                return false;
            }
            synchronized (transfer) {
                if (transfer.sent || transfer.cancelled || transfer.headers.size() >= 36) {
                    return false;
                }
                transfer.headers.put(name, value);
            }
            return true;
        } catch (Exception error) {
            return false;
        }
    }

    boolean send(int id, byte[] body) {
        Transfer transfer = transfers.get(id);
        if (transfer == null || body == null || body.length > LIMIT) {
            return false;
        }
        synchronized (transfer) {
            if (transfer.sent || transfer.cancelled) {
                return false;
            }
            transfer.sent = true;
            transfer.worker = workers.submit(() -> perform(id, transfer, body));
        }
        return true;
    }

    private void expire(int id, Transfer transfer) {
        // Also reclaim completed responses whose native caller lost its JNI
        // attachment or stopped polling. A handle never outlives its deadline.
        if (!transfers.remove(id, transfer)) {
            return;
        }
        synchronized (transfer) {
            transfer.cancelled = true;
            transfer.state = 0;
            transfer.response = null;
        }
        stop(transfer);
    }

    private static void stop(Transfer transfer) {
        Future<?> worker = transfer.worker;
        if (worker != null) {
            worker.cancel(true);
        }
        HttpURLConnection connection = transfer.connection;
        if (connection != null) {
            connection.disconnect();
        }
    }

    private void perform(int id, Transfer transfer, byte[] body) {
        HttpURLConnection connection = null;
        int status = 0;
        byte[] response = null;
        try {
            if (transfer.cancelled) {
                return;
            }
            connection = (HttpURLConnection)transfer.url.openConnection();
            transfer.connection = connection;
            connection.setInstanceFollowRedirects(false);
            connection.setUseCaches(false);
            connection.setConnectTimeout(Math.min(15000, transfer.timeout));
            connection.setReadTimeout(Math.min(30000, transfer.timeout));
            connection.setRequestMethod(transfer.method);
            // System HTTPS trust and hostname verification are left intact.
            for (Map.Entry<String, String> header : transfer.headers.entrySet()) {
                connection.setRequestProperty(header.getKey(), header.getValue());
            }
            if (transfer.cancelled) {
                return;
            }
            if (body.length > 0) {
                connection.setDoOutput(true);
                connection.setFixedLengthStreamingMode(body.length);
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(body);
                }
            }
            int receivedStatus = connection.getResponseCode();
            if (connection.getContentLength() >= transfer.capacity) {
                throw new java.io.IOException("response capacity exceeded");
            }
            InputStream stream = receivedStatus >= 400
                ? connection.getErrorStream() : connection.getInputStream();
            ByteArrayOutputStream bytes = new ByteArrayOutputStream(
                Math.min(transfer.capacity - 1, 8192));
            if (stream != null) {
                try (InputStream input = stream) {
                    byte[] buffer = new byte[Math.min(transfer.capacity, 8192)];
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        if (transfer.cancelled || count > transfer.capacity - bytes.size() - 1) {
                            throw new java.io.IOException("response cancelled or capacity exceeded");
                        }
                        bytes.write(buffer, 0, count);
                    }
                }
            }
            response = bytes.toByteArray();
            status = receivedStatus;
        } catch (Exception error) {
            // Transport errors are reported without logging credentials or response data.
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
            transfer.connection = null;
            synchronized (transfer) {
                if (!transfer.cancelled && transfers.get(id) == transfer) {
                    transfer.response = response;
                    transfer.state = status;
                }
            }
        }
    }

    int poll(int id) {
        Transfer transfer = transfers.get(id);
        if (transfer == null) {
            return 0;
        }
        synchronized (transfer) {
            return transfer.sent ? transfer.state : 0;
        }
    }

    byte[] response(int id) {
        Transfer transfer = transfers.get(id);
        if (transfer == null) {
            return null;
        }
        synchronized (transfer) {
            return transfer.state > 0 ? transfer.response : null;
        }
    }

    void cancel(int id) {
        Transfer transfer = transfers.remove(id);
        if (transfer == null) {
            return;
        }
        synchronized (transfer) {
            transfer.cancelled = true;
            transfer.response = null;
        }
        ScheduledFuture<?> timer = transfer.timer;
        if (timer != null) {
            timer.cancel(false);
        }
        stop(transfer);
    }

    synchronized void close() {
        closed = true;
        for (Integer id : transfers.keySet()) {
            cancel(id);
        }
        workers.shutdownNow();
        timers.shutdownNow();
    }
}
