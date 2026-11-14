package dev.blueprint.builder;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.block.BlockState;
import org.bukkit.block.data.BlockData;
import org.bukkit.entity.Player;
import org.bukkit.scheduler.BukkitRunnable;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

/** 템플릿 자동 건축 / 취소 / 되돌리기. 모든 메서드는 메인 스레드에서 호출해야 한다. */
public final class BuildManager {

    /** 다른 블록에 붙어야 하는 블록은 나중에 설치한다. */
    private static final Pattern ATTACHED = Pattern.compile(
            "torch|lantern|ladder|door|button|lever|sign|banner|carpet|rail|flower|sapling|azalea|"
                    + "pressure_plate|tripwire|vine|bed|candle|pot|bell|chain|redstone_wire|repeater|comparator");
    private static final int UNDO_HISTORY = 5;

    private record Placement(Location location, BlockData data) {}

    /** 되돌리기용 원래 블록 상태 (상자 내용물, 표지판 글 등 블록 엔티티 데이터 포함). */
    private record Previous(BlockState state) {}

    private final BlueprintPlugin plugin;
    private final Map<UUID, BuildTask> active = new HashMap<>();
    private final Map<UUID, Deque<List<Previous>>> history = new HashMap<>();

    public BuildManager(BlueprintPlugin plugin) {
        this.plugin = plugin;
    }

    public boolean isBuilding(UUID player) {
        return active.containsKey(player);
    }

    /** 템플릿 JSON을 플레이어 앞에 짓기 시작한다. */
    public void start(Player player, String name, JsonObject data) {
        JsonArray size = data.getAsJsonArray("size");
        JsonArray palette = data.getAsJsonArray("palette");
        JsonArray blocks = data.getAsJsonArray("blocks");
        int maxBlocks = plugin.getConfig().getInt("build.max-blocks", 50000);
        if (blocks.size() > maxBlocks) {
            player.sendRichMessage("<red>블록이 너무 많습니다. (" + blocks.size() + " > 서버 제한 " + maxBlocks + ")");
            return;
        }

        Orientation o = Orientation.of(player.getFacing());
        int sx = size.get(0).getAsInt();
        int distance = plugin.getConfig().getInt("build.distance", 2);
        Location base = player.getLocation().getBlock().getLocation();
        World world = base.getWorld();

        // 팔레트 → BlockData (회전 적용). 이 서버 버전에 없는 블록은 건너뛴다.
        BlockData[] parsed = new BlockData[palette.size()];
        List<String> unknown = new ArrayList<>();
        for (int i = 0; i < palette.size(); i++) {
            String s = palette.get(i).getAsString();
            try {
                BlockData bd = Bukkit.createBlockData(s);
                bd.rotate(o.rotation);
                parsed[i] = bd;
            } catch (IllegalArgumentException e) {
                unknown.add(s);
            }
        }

        List<Placement> solid = new ArrayList<>();
        List<Placement> attached = new ArrayList<>();
        int offsetX = -(sx / 2);
        for (JsonElement el : blocks) {
            JsonArray b = el.getAsJsonArray();
            int lx = b.get(0).getAsInt() + offsetX;
            int ly = b.get(1).getAsInt();
            int lz = b.get(2).getAsInt() + distance;
            BlockData bd = parsed[b.get(3).getAsInt()];
            if (bd == null) continue;
            int wy = base.getBlockY() + ly;
            if (wy < world.getMinHeight() || wy >= world.getMaxHeight()) continue;
            Location loc = base.clone().add(o.worldX(lx, lz), ly, o.worldZ(lx, lz));
            (ATTACHED.matcher(bd.getMaterial().getKey().getKey()).find() ? attached : solid).add(new Placement(loc, bd));
        }
        Comparator<Placement> byY = Comparator.comparingInt(p -> p.location.getBlockY());
        solid.sort(byY);
        attached.sort(byY);
        List<Placement> order = new ArrayList<>(solid.size() + attached.size());
        order.addAll(solid);
        order.addAll(attached);

        if (!unknown.isEmpty()) {
            player.sendRichMessage("<yellow>이 서버 버전에서 알 수 없는 블록 " + unknown.size() + "종은 건너뜁니다: <gray>"
                    + String.join(", ", unknown.subList(0, Math.min(3, unknown.size()))));
        }
        BuildTask task = new BuildTask(player, name, order);
        active.put(player.getUniqueId(), task);
        task.runTaskTimer(plugin, 1L, 1L);
        player.sendRichMessage("<green>건축 시작: <white>" + Text.escape(name) + "</white> <gray>("
                + order.size() + "블록, 바라보는 방향 " + o.name() + ") · 취소: /tb cancel");
    }

    public boolean cancel(UUID player) {
        BuildTask task = active.get(player);
        if (task == null) return false;
        task.finish(true);
        return true;
    }

    /** 마지막 건축을 원래 상태로 되돌린다. 되돌린 블록 수, 기록이 없으면 -1. */
    public int undo(UUID player) {
        if (isBuilding(player)) cancel(player);
        Deque<List<Previous>> stack = history.get(player);
        if (stack == null || stack.isEmpty()) return -1;
        List<Previous> prev = stack.pop();
        for (int i = prev.size() - 1; i >= 0; i--) {
            prev.get(i).state.update(true, false);
        }
        return prev.size();
    }

    public void shutdown() {
        new ArrayList<>(active.values()).forEach(t -> t.finish(true));
        history.clear();
    }

    private final class BuildTask extends BukkitRunnable {
        private final Player player;
        private final UUID uuid;
        private final String name;
        private final List<Placement> order;
        private final List<Previous> previous = new ArrayList<>();
        private final int perTick;
        private final boolean effects;
        private int index;
        private boolean finished;

        BuildTask(Player player, String name, List<Placement> order) {
            this.player = player;
            this.uuid = player.getUniqueId();
            this.name = name;
            this.order = order;
            this.perTick = Math.max(1, plugin.getConfig().getInt("build.blocks-per-tick", 40));
            this.effects = plugin.getConfig().getBoolean("build.effects", true);
        }

        @Override
        public void run() {
            int end = Math.min(order.size(), index + perTick);
            Placement last = null;
            for (; index < end; index++) {
                Placement p = order.get(index);
                Block block = p.location.getBlock();
                BlockData current = block.getBlockData();
                if (current.matches(p.data)) continue;
                previous.add(new Previous(block.getState()));
                block.setBlockData(p.data, false);
                last = p;
            }
            if (effects && last != null && player.isOnline()) {
                Location at = last.location.clone().add(0.5, 0.5, 0.5);
                at.getWorld().spawnParticle(Particle.CLOUD, at, 3, 0.2, 0.2, 0.2, 0.01);
                if (index % (perTick * 4) < perTick) {
                    at.getWorld().playSound(at, last.data.getSoundGroup().getPlaceSound(), 0.6f, 1f);
                }
            }
            if (player.isOnline() && index % (perTick * 20) < perTick) {
                int pct = order.isEmpty() ? 100 : index * 100 / order.size();
                player.sendActionBar(Text.mini("<gold>건축 중 <white>" + Text.escape(name) + "</white> " + pct + "%"));
            }
            if (index >= order.size()) finish(false);
        }

        void finish(boolean cancelled) {
            if (finished) return;
            finished = true;
            cancel();
            active.remove(uuid);
            if (!previous.isEmpty()) {
                Deque<List<Previous>> stack = history.computeIfAbsent(uuid, k -> new ArrayDeque<>());
                stack.push(previous);
                while (stack.size() > UNDO_HISTORY) stack.removeLast();
            }
            if (player.isOnline()) {
                if (cancelled) {
                    player.sendRichMessage("<yellow>건축을 중단했습니다. <gray>(" + index + "/" + order.size()
                            + "블록) · /tb undo 로 되돌릴 수 있습니다.");
                } else {
                    player.sendActionBar(Text.mini("<green>건축 완료!"));
                    player.sendRichMessage("<green>건축 완료: <white>" + Text.escape(name)
                            + "</white> <gray>· 마음에 안 들면 /tb undo");
                    player.playSound(player.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 0.7f, 1.2f);
                }
            }
        }
    }
}
