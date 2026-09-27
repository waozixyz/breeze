package xyz.waozi.inbe;

import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpsServer;
import com.sun.net.httpserver.HttpsConfigurator;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import java.util.Arrays;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

public final class AndroidHttpTransportTest {
    private static byte[] bytes(String text) {
        return text.getBytes(StandardCharsets.UTF_8);
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static int request(HttpTransport transport, String method, String url,
                               int capacity, int timeout, byte[] body) {
        int id = transport.create(bytes(method), bytes(url), capacity, timeout);
        require(id > 0, "create request");
        require(transport.send(id, body), "send request");
        return id;
    }

    private static int waitFor(HttpTransport transport, int id) throws Exception {
        long end = System.nanoTime() + 5_000_000_000L;
        int result;
        while ((result = transport.poll(id)) < 0 && System.nanoTime() < end) {
            Thread.sleep(5);
        }
        require(result >= 0, "request deadline");
        return result;
    }

    public static void main(String[] args) throws Exception {
        HttpTransport transport = new HttpTransport();
        ExecutorService serverWorkers = Executors.newCachedThreadPool();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.setExecutor(serverWorkers);
        server.createContext("/echo", exchange -> {
            byte[] body = exchange.getRequestBody().readAllBytes();
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.createContext("/missing", exchange -> {
            byte[] body = bytes("missing");
            exchange.sendResponseHeaders(404, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.createContext("/large", exchange -> {
            byte[] body = bytes("123456789");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.createContext("/chunked", exchange -> {
            exchange.sendResponseHeaders(200, 0);
            exchange.getResponseBody().write(bytes("123456789"));
            exchange.close();
        });
        server.createContext("/redirect", exchange -> {
            exchange.getResponseHeaders().add("Location", "/missing");
            exchange.sendResponseHeaders(302, -1);
            exchange.close();
        });
        server.createContext("/slow", exchange -> {
            try {
                Thread.sleep(300);
                exchange.sendResponseHeaders(200, 4);
                exchange.getResponseBody().write(bytes("late"));
            } catch (Exception ignored) {
                // Cancellation closes this connection before the delayed response.
            } finally {
                exchange.close();
            }
        });
        KeyStore keys = KeyStore.getInstance("PKCS12");
        try (var input = Files.newInputStream(Path.of(args[0]))) {
            keys.load(input, "password".toCharArray());
        }
        KeyManagerFactory managers = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        managers.init(keys, "password".toCharArray());
        SSLContext tls = SSLContext.getInstance("TLS");
        tls.init(managers.getKeyManagers(), null, null);
        HttpsServer secure = HttpsServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        secure.setHttpsConfigurator(new HttpsConfigurator(tls));
        secure.setExecutor(serverWorkers);
        secure.createContext("/", exchange -> {
            exchange.sendResponseHeaders(200, 2);
            exchange.getResponseBody().write(bytes("ok"));
            exchange.close();
        });
        server.start();
        secure.start();
        String base = "http://127.0.0.1:" + server.getAddress().getPort();
        String secureBase = "https://localhost:" + secure.getAddress().getPort();
        try {
            require(transport.create(bytes("GET"), bytes("file:///tmp/no"), 64, 1000) == 0,
                "reject non HTTP scheme");
            require(transport.create(bytes("GET"), bytes(base), 16777217, 1000) == 0,
                "hard response allocation limit");
            int id = transport.create(bytes("POST"), bytes(base + "/echo"), 64, 1000);
            require(!transport.header(id, bytes("X-Test"), bytes("bad\r\nInjected: value")),
                "reject injected header");
            byte[] binary = new byte[] {65, 0, 66, (byte)0xf0, (byte)0x9f, (byte)0x99, (byte)0x82};
            require(transport.send(id, binary), "send binary body");
            require(waitFor(transport, id) == 200 && Arrays.equals(transport.response(id), binary),
                "preserve raw bytes");
            transport.cancel(id);
            id = request(transport, "GET", base + "/missing", 64, 1000, new byte[0]);
            require(waitFor(transport, id) == 404 && Arrays.equals(transport.response(id), bytes("missing")),
                "HTTP errors retain status and body");
            transport.cancel(id);
            for (String path : new String[] {"/large", "/chunked"}) {
                id = request(transport, "GET", base + path, 8, 1000, new byte[0]);
                require(waitFor(transport, id) == 0 && transport.response(id) == null,
                    "bounded response " + path);
                transport.cancel(id);
            }
            id = request(transport, "GET", base + "/redirect", 64, 1000, new byte[0]);
            require(waitFor(transport, id) == 302, "never follow redirect");
            transport.cancel(id);
            id = request(transport, "GET", base + "/slow", 64, 30, new byte[0]);
            require(waitFor(transport, id) == 0, "enforce deadline");
            transport.cancel(id);
            id = request(transport, "GET", base + "/slow", 64, 1000, new byte[0]);
            transport.cancel(id);
            Thread.sleep(400);
            require(transport.poll(id) == 0 && transport.response(id) == null,
                "cancel prevents late publication");
            id = request(transport, "GET", base + "/missing", 64, 100, new byte[0]);
            require(waitFor(transport, id) == 404, "orphan initially completes");
            Thread.sleep(150);
            require(transport.poll(id) == 0 && transport.response(id) == null,
                "deadline reclaims completed response if caller lost its JNI handle");
            id = request(transport, "GET", secureBase, 64, 1000, new byte[0]);
            require(waitFor(transport, id) == 0, "reject untrusted certificate");
            transport.cancel(id);
            TrustManagerFactory trust = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
            trust.init(keys);
            SSLContext client = SSLContext.getInstance("TLS");
            client.init(null, trust.getTrustManagers(), null);
            HttpsURLConnection.setDefaultSSLSocketFactory(client.getSocketFactory());
            id = request(transport, "GET", secureBase, 64, 1000, new byte[0]);
            require(waitFor(transport, id) == 200, "accept trusted matching hostname");
            transport.cancel(id);
            id = request(transport, "GET", secureBase.replace("localhost", "127.0.0.1"),
                64, 1000, new byte[0]);
            require(waitFor(transport, id) == 0, "reject certificate hostname mismatch");
            transport.cancel(id);
            require(transport.create(bytes("GET"), bytes(base), 64, 20) > 0,
                "create abandoned configuration");
            Thread.sleep(50);
            int[] handles = new int[8];
            for (int index = 0; index < handles.length; index++) {
                handles[index] = transport.create(bytes("GET"), bytes(base), 64, 1000);
                require(handles[index] > 0, "bounded request slot");
            }
            require(transport.create(bytes("GET"), bytes(base), 64, 1000) == 0, "slot cap");
            for (int handle : handles) {
                transport.cancel(handle);
            }
        } finally {
            transport.close();
            server.stop(0);
            secure.stop(0);
            serverWorkers.shutdownNow();
        }
        System.out.println("Android HTTPS bounds, cancellation, certificate and hostname checks passed");
    }
}
