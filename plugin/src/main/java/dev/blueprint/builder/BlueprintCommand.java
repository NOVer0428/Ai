package dev.blueprint.builder;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.block.Block;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabExecutor;
import org.bukkit.entity.Player;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

public final class BlueprintCommand implements TabExecutor {

    private static final List<String> SUBS = List.of(
            "help", "link", "unlink", "status", "list", "build", "cancel", "undo", "pos1", "pos2", "save", "reload");

    private record Entry(int id, String name, String size, int blocks) {}

    private final BlueprintPlugin plugin;
    /** /tb list 로 받은 보관함 목록 (번호 → 템플릿 id 매핑용). */
    private final Map<UUID, List<Entry>> listCache = new HashMap<>();
    private final Map<UUID, Location[]> selections = new HashMap<>();
    /** 템플릿을 받아오는 중인 건축 요청. cancel/undo 하면 지워져서 응답이 와도 짓지 않는다. */
    private final Map<UUID, Integer> pendingBuilds = new HashMap<>();
    private int buildSeq;

    public BlueprintCommand(BlueprintPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        try {
            return handle(sender, args);
        } catch (RuntimeException e) {
            plugin.getLogger().log(java.util.logging.Level.WARNING, "/tb 처리 중 오류", e);
            sender.sendRichMessage("<red>명령어 처리 중 오류가 났습니다: <white>" + Text.escape(String.valueOf(e.getMessage()))
                    + "</white> <gray>(자세한 내용은 서버 콘솔)");
            return true;
        }
    }

    private boolean handle(CommandSender sender, String[] args) {
        String sub = args.length == 0 ? "help" : args[0].toLowerCase();
        if (sub.equals("reload")) {
            if (!sender.hasPermission("blueprint.admin")) {
                sender.sendRichMessage("<red>권한이 없습니다.");
                return true;
            }
            plugin.reload();
            sender.sendRichMessage("<green>설정을 다시 불러왔습니다.");
            return true;
        }
        if (!(sender instanceof Player p)) {
            sender.sendRichMessage("<red>플레이어만 사용할 수 있습니다.");
            return true;
        }
        if (!p.hasPermission("blueprint.use")) {
            p.sendRichMessage("<red>권한이 없습니다.");
            return true;
        }
        switch (sub) {
            case "link" -> link(p, args);
            case "unlink" -> call(p, plugin.api().unlink(p.getUniqueId()), r -> {
                listCache.remove(p.getUniqueId());
                p.sendRichMessage("<yellow>웹사이트 계정 연동을 해제했습니다.");
            });
            case "status" -> call(p, plugin.api().player(p.getUniqueId()),
                    r -> p.sendRichMessage("<green>연동된 웹 계정: <white>" + Text.escape(r.get("username").getAsString())));
            case "list" -> list(p);
            case "build" -> build(p, args);
            case "cancel" -> {
                boolean pending = pendingBuilds.remove(p.getUniqueId()) != null;
                if (!plugin.builds().cancel(p.getUniqueId())) {
                    p.sendRichMessage(pending ? "<yellow>건축 요청을 취소했습니다." : "<gray>진행 중인 건축이 없습니다.");
                }
            }
            case "undo" -> {
                pendingBuilds.remove(p.getUniqueId());
                int n = plugin.builds().undo(p.getUniqueId());
                p.sendRichMessage(n < 0 ? "<gray>되돌릴 건축 기록이 없습니다." : "<green>" + n + "개 블록을 원래대로 되돌렸습니다.");
            }
            case "pos1", "pos2" -> pos(p, sub.equals("pos1") ? 0 : 1);
            case "save" -> save(p, args);
            default -> help(p);
        }
        return true;
    }

    private void help(Player p) {
        String url = plugin.getConfig().getString("api-url", "");
        p.sendRichMessage("""
                <gold><bold>블루프린트</bold> <gray>- 웹사이트 보관함의 건물을 자동 건축
                <yellow>/tb link <코드></yellow> <gray>웹사이트 '내 보관함'에서 받은 코드로 계정 연동
                <yellow>/tb list</yellow> <gray>내 보관함 목록
                <yellow>/tb build <번호></yellow> <gray>바라보는 방향 앞에 건축
                <yellow>/tb cancel</yellow> <gray>건축 중단  <yellow>/tb undo</yellow> <gray>마지막 건축 되돌리기
                <yellow>/tb pos1</yellow>, <yellow>/tb pos2</yellow>, <yellow>/tb save <이름></yellow> <gray>영역을 템플릿으로 업로드
                <yellow>/tb status</yellow>, <yellow>/tb unlink</yellow> <gray>연동 확인/해제""" +
                (url.isEmpty() ? "" : "\n<gray>웹사이트: <aqua><click:open_url:'" + url + "'>" + Text.escape(url) + "</click>"));
    }

    private void link(Player p, String[] args) {
        if (args.length < 2) {
            p.sendRichMessage("<red>사용법: /tb link <코드> <gray>(웹사이트 '내 보관함'에서 연동 코드를 발급받으세요)");
            return;
        }
        String code = args[1].trim().toUpperCase();
        call(p, plugin.api().link(p.getUniqueId(), p.getName(), code), r -> {
            listCache.remove(p.getUniqueId());
            p.sendRichMessage("<green>연동 완료! 웹 계정 <white>" + Text.escape(r.get("username").getAsString())
                    + "</white> 과 연결되었습니다. <gray>/tb list 로 보관함을 확인하세요.");
        });
    }

    private void list(Player p) {
        call(p, plugin.api().library(p.getUniqueId()), r -> {
            List<Entry> entries = parseEntries(r);
            listCache.put(p.getUniqueId(), entries);
            if (entries.isEmpty()) {
                p.sendRichMessage("<gray>보관함이 비어 있습니다. 웹사이트에서 템플릿을 담아주세요.");
                return;
            }
            StringBuilder sb = new StringBuilder("<gold>" + Text.escape(r.get("username").getAsString()) + "님의 보관함 <gray>(" + entries.size() + ")");
            for (int i = 0; i < entries.size(); i++) {
                Entry e = entries.get(i);
                sb.append("\n<click:suggest_command:'/tb build ").append(i + 1).append("'>")
                        .append("<hover:show_text:'클릭해서 건축 명령어 입력'>")
                        .append("<yellow>").append(i + 1).append(". <white>").append(Text.escape(e.name))
                        .append(" <gray>").append(e.size).append(" · ").append(e.blocks).append("블록</hover></click>");
            }
            sb.append("\n<gray>건축: /tb build <번호>");
            p.sendRichMessage(sb.toString());
        });
    }

    private static List<Entry> parseEntries(JsonObject r) {
        List<Entry> out = new ArrayList<>();
        for (JsonElement el : r.getAsJsonArray("templates")) {
            JsonObject t = el.getAsJsonObject();
            JsonArray s = t.getAsJsonArray("size");
            out.add(new Entry(t.get("id").getAsInt(), t.get("name").getAsString(),
                    s.get(0).getAsInt() + "×" + s.get(1).getAsInt() + "×" + s.get(2).getAsInt(),
                    t.get("blockCount").getAsInt()));
        }
        return out;
    }

    private void build(Player p, String[] args) {
        if (args.length < 2) {
            p.sendRichMessage("<red>사용법: /tb build <번호> <gray>(/tb list 의 번호)");
            return;
        }
        int number;
        try {
            number = Integer.parseInt(args[1]);
        } catch (NumberFormatException e) {
            p.sendRichMessage("<red>번호는 숫자로 입력하세요. 예: /tb build 1");
            return;
        }
        if (plugin.builds().isBuilding(p.getUniqueId()) || pendingBuilds.containsKey(p.getUniqueId())) {
            p.sendRichMessage("<red>이미 건축 중입니다. /tb cancel 로 중단할 수 있습니다.");
            return;
        }
        int seq = ++buildSeq;
        pendingBuilds.put(p.getUniqueId(), seq);
        // 항상 최신 보관함 목록 기준으로 번호를 해석한다
        call(p, plugin.api().library(p.getUniqueId()), r -> {
            if (!isPending(p, seq)) return;
            List<Entry> entries = parseEntries(r);
            listCache.put(p.getUniqueId(), entries);
            if (number < 1 || number > entries.size()) {
                pendingBuilds.remove(p.getUniqueId());
                p.sendRichMessage("<red>" + number + "번 템플릿이 없습니다. <gray>보관함: " + entries.size() + "개 (/tb list)");
                return;
            }
            Entry e = entries.get(number - 1);
            p.sendRichMessage("<gray>'" + Text.escape(e.name) + "' 템플릿을 불러오는 중...");
            call(p, plugin.api().template(p.getUniqueId(), e.id), t -> {
                if (!isPending(p, seq)) return;
                pendingBuilds.remove(p.getUniqueId());
                plugin.builds().start(p, t.get("name").getAsString(), t.getAsJsonObject("data"));
            });
        });
    }

    private void pos(Player p, int which) {
        Block target = p.getTargetBlockExact(8);
        Location loc = (target != null ? target.getLocation() : p.getLocation().getBlock().getLocation());
        Location[] sel = selections.computeIfAbsent(p.getUniqueId(), k -> new Location[2]);
        sel[which] = loc;
        p.sendRichMessage("<green>pos" + (which + 1) + " 설정: <white>" + loc.getBlockX() + ", " + loc.getBlockY() + ", " + loc.getBlockZ()
                + (target == null ? " <gray>(발 위치)" : " <gray>(바라보는 블록)"));
    }

    private void save(Player p, String[] args) {
        if (!p.hasPermission("blueprint.save")) {
            p.sendRichMessage("<red>권한이 없습니다.");
            return;
        }
        if (args.length < 2) {
            p.sendRichMessage("<red>사용법: /tb save <이름>");
            return;
        }
        Location[] sel = selections.get(p.getUniqueId());
        if (sel == null || sel[0] == null || sel[1] == null) {
            p.sendRichMessage("<red>먼저 /tb pos1, /tb pos2 로 영역을 지정하세요.");
            return;
        }
        if (!sel[0].getWorld().equals(sel[1].getWorld())) {
            p.sendRichMessage("<red>pos1 과 pos2 가 서로 다른 월드에 있습니다.");
            return;
        }
        int max = plugin.getConfig().getInt("save.max-size", 64);
        int dx = Math.abs(sel[0].getBlockX() - sel[1].getBlockX()) + 1;
        int dy = Math.abs(sel[0].getBlockY() - sel[1].getBlockY()) + 1;
        int dz = Math.abs(sel[0].getBlockZ() - sel[1].getBlockZ()) + 1;
        if (dx > max || dy > max || dz > max) {
            p.sendRichMessage("<red>영역이 너무 큽니다. 한 변 최대 " + max + "칸 (현재 " + dx + "×" + dy + "×" + dz + ")");
            return;
        }
        String name = String.join(" ", Arrays.copyOfRange(args, 1, args.length));
        if (name.length() > 40) name = name.substring(0, 40);
        JsonObject data = Capture.capture(sel[0], sel[1], Orientation.of(p.getFacing()));
        if (data.getAsJsonArray("blocks").isEmpty()) {
            p.sendRichMessage("<red>영역 안에 블록이 없습니다.");
            return;
        }
        String finalName = name;
        p.sendRichMessage("<gray>업로드 중... (" + data.getAsJsonArray("blocks").size() + "블록)");
        call(p, plugin.api().upload(p.getUniqueId(), name, data), r -> p.sendRichMessage(
                "<green>'" + Text.escape(finalName) + "' 를 업로드하고 보관함에 담았습니다. <gray>지금 바라보는 방향이 정면입니다."));
    }

    private boolean isPending(Player p, int seq) {
        Integer cur = pendingBuilds.get(p.getUniqueId());
        return cur != null && cur == seq;
    }

    /** 비동기 API 호출 결과를 메인 스레드에서 처리하고, 오류는 플레이어에게 알린다. */
    private void call(Player p, CompletableFuture<JsonObject> future, Consumer<JsonObject> onSuccess) {
        future.whenComplete((res, ex) -> Bukkit.getScheduler().runTask(plugin, () -> {
            if (!p.isOnline()) return;
            if (ex == null) {
                try {
                    onSuccess.accept(res);
                } catch (RuntimeException e) {
                    pendingBuilds.remove(p.getUniqueId());
                    p.sendRichMessage("<red>웹사이트 응답을 처리하지 못했습니다. (" + Text.escape(String.valueOf(e.getMessage())) + ")");
                    plugin.getLogger().warning("응답 처리 실패: " + e);
                }
                return;
            }
            pendingBuilds.remove(p.getUniqueId());
            String msg = ApiClient.errorMessage(ex);
            p.sendRichMessage("<red>" + Text.escape(msg));
            if (ApiClient.errorStatus(ex) == 404 && msg.contains("연동되지 않은")) {
                p.sendRichMessage("<gray>웹사이트 '내 보관함'에서 연동 코드를 발급받아 <yellow>/tb link <코드></yellow> 를 입력하세요.");
            } else if (ApiClient.errorStatus(ex) == 401) {
                plugin.getLogger().warning("웹사이트가 API 키를 거부했습니다. config.yml 의 api-key 를 확인하세요.");
            }
        }));
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length == 1) {
            return SUBS.stream().filter(s -> s.startsWith(args[0].toLowerCase())).toList();
        }
        if (args.length == 2 && args[0].equalsIgnoreCase("build") && sender instanceof Player p) {
            List<Entry> entries = listCache.getOrDefault(p.getUniqueId(), List.of());
            List<String> out = new ArrayList<>();
            for (int i = 1; i <= entries.size(); i++) out.add(String.valueOf(i));
            return out;
        }
        return List.of();
    }
}
