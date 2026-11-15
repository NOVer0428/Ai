package dev.blueprint.builder;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/** 웹사이트의 /api/plugin/* 엔드포인트를 호출한다. 모든 메서드는 비동기(별도 스레드)로 완료된다. */
public final class ApiClient {

    /** 서버가 돌려준 오류 (상태 코드 + 한국어 메시지). */
    public static final class ApiException extends RuntimeException {
        public final int status;

        public ApiException(int status, String message) {
            super(message);
            this.status = status;
        }
    }

    private static final Gson GSON = new Gson();
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    private final String baseUrl;
    private final String apiKey;

    public ApiClient(String baseUrl, String apiKey) {
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.apiKey = apiKey;
    }

    /** 설정값 문제를 한국어로 설명한다. 문제가 없으면 null. */
    public String configProblem() {
        if (apiKey == null || apiKey.isBlank() || apiKey.startsWith("여기에")) {
            return "서버 관리자가 아직 API 키를 설정하지 않았습니다. (plugins/BlueprintBuilder/config.yml 의 api-key)";
        }
        if (!apiKey.chars().allMatch(c -> c > 32 && c < 127)) {
            return "config.yml 의 api-key 에 영문·숫자 외 문자(한글·공백 등)가 들어 있습니다.";
        }
        if (!baseUrl.matches("https?://[^\\s]+")) {
            return "config.yml 의 api-url 이 올바른 주소가 아닙니다. (예: http://127.0.0.1:5000)";
        }
        return null;
    }

    public CompletableFuture<JsonObject> link(UUID uuid, String name, String code) {
        JsonObject body = new JsonObject();
        body.addProperty("uuid", uuid.toString());
        body.addProperty("name", name);
        body.addProperty("code", code);
        return send("POST", "/api/plugin/link", body);
    }

    public CompletableFuture<JsonObject> player(UUID uuid) {
        return send("GET", "/api/plugin/players/" + uuid, null);
    }

    public CompletableFuture<JsonObject> unlink(UUID uuid) {
        return send("POST", "/api/plugin/players/" + uuid + "/unlink", new JsonObject());
    }

    public CompletableFuture<JsonObject> library(UUID uuid) {
        return send("GET", "/api/plugin/players/" + uuid + "/library", null);
    }

    public CompletableFuture<JsonObject> template(UUID uuid, int id) {
        return send("GET", "/api/plugin/players/" + uuid + "/templates/" + id, null);
    }

    public CompletableFuture<JsonObject> upload(UUID uuid, String name, JsonObject data) {
        JsonObject body = new JsonObject();
        body.addProperty("name", name);
        body.addProperty("category", "인게임");
        body.addProperty("description", "인게임에서 /tb save 로 저장한 템플릿");
        body.add("data", data);
        return send("POST", "/api/plugin/players/" + uuid + "/templates", body);
    }

    private CompletableFuture<JsonObject> send(String method, String path, JsonObject body) {
        String problem = configProblem();
        if (problem != null) return CompletableFuture.failedFuture(new ApiException(0, problem));
        HttpRequest built;
        try {
            HttpRequest.Builder req = HttpRequest.newBuilder(URI.create(baseUrl + path))
                    .timeout(Duration.ofSeconds(15))
                    .header("Authorization", "Bearer " + apiKey)
                    .header("Accept", "application/json");
            if (body != null) {
                req.header("Content-Type", "application/json");
                req.method(method, HttpRequest.BodyPublishers.ofString(GSON.toJson(body), StandardCharsets.UTF_8));
            } else {
                req.method(method, HttpRequest.BodyPublishers.noBody());
            }
            built = req.build();
        } catch (IllegalArgumentException e) {
            return CompletableFuture.failedFuture(new ApiException(0,
                    "플러그인 설정이 잘못되었습니다. config.yml 의 api-url/api-key 를 확인하세요. (" + e.getMessage() + ")"));
        }
        return http.sendAsync(built, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8))
                .handle((res, ex) -> {
                    if (ex != null) {
                        throw new ApiException(0, "웹사이트에 연결할 수 없습니다. (" + rootMessage(ex) + ")");
                    }
                    JsonObject json = parse(res.body());
                    if (res.statusCode() >= 400) {
                        String msg = json != null && json.has("error")
                                ? json.get("error").getAsString()
                                : "웹사이트 오류 (HTTP " + res.statusCode() + ")";
                        throw new ApiException(res.statusCode(), msg);
                    }
                    return json != null ? json : new JsonObject();
                });
    }

    private static JsonObject parse(String text) {
        try {
            JsonElement el = JsonParser.parseString(text);
            return el.isJsonObject() ? el.getAsJsonObject() : null;
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static String rootMessage(Throwable t) {
        while (t.getCause() != null) {
            t = t.getCause();
        }
        return t.getClass().getSimpleName() + (t.getMessage() != null ? ": " + t.getMessage() : "");
    }

    /** CompletableFuture 예외에서 사용자에게 보여줄 메시지를 꺼낸다. */
    public static String errorMessage(Throwable t) {
        Throwable cur = t;
        while (cur != null) {
            if (cur instanceof ApiException api) return api.getMessage();
            cur = cur.getCause();
        }
        return "알 수 없는 오류: " + t;
    }

    public static int errorStatus(Throwable t) {
        Throwable cur = t;
        while (cur != null) {
            if (cur instanceof ApiException api) return api.status;
            cur = cur.getCause();
        }
        return -1;
    }
}
