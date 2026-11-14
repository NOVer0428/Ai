package dev.blueprint.builder;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.data.BlockData;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 월드의 직육면체 영역을 템플릿 JSON 으로 변환한다 (/tb save). */
final class Capture {
    private Capture() {}

    /**
     * @param o 저장하는 플레이어가 바라보는 방향. 플레이어 쪽을 향한 면이 템플릿의 정면(z = 0)이 된다.
     *          같은 방향을 보고 /tb build 하면 저장할 때와 똑같은 모습으로 지어진다.
     */
    static JsonObject capture(Location a, Location b, Orientation o) {
        World world = a.getWorld();
        int minX = Math.min(a.getBlockX(), b.getBlockX()), maxX = Math.max(a.getBlockX(), b.getBlockX());
        int minY = Math.min(a.getBlockY(), b.getBlockY()), maxY = Math.max(a.getBlockY(), b.getBlockY());
        int minZ = Math.min(a.getBlockZ(), b.getBlockZ()), maxZ = Math.max(a.getBlockZ(), b.getBlockZ());

        record Cell(int lx, int ly, int lz, String data) {}
        List<Cell> cells = new ArrayList<>();
        int loX = Integer.MAX_VALUE, loZ = Integer.MAX_VALUE, hiX = Integer.MIN_VALUE, hiZ = Integer.MIN_VALUE;
        for (int x = minX; x <= maxX; x++) {
            for (int z = minZ; z <= maxZ; z++) {
                int lx = o.localX(x - minX, z - minZ);
                int lz = o.localZ(x - minX, z - minZ);
                loX = Math.min(loX, lx); hiX = Math.max(hiX, lx);
                loZ = Math.min(loZ, lz); hiZ = Math.max(hiZ, lz);
                for (int y = minY; y <= maxY; y++) {
                    BlockData bd = world.getBlockAt(x, y, z).getBlockData();
                    Material m = bd.getMaterial();
                    if (m.isAir() || m == Material.STRUCTURE_VOID) continue;
                    BlockData local = bd.clone();
                    local.rotate(o.inverse());
                    cells.add(new Cell(lx, y - minY, lz, local.getAsString()));
                }
            }
        }

        Map<String, Integer> index = new LinkedHashMap<>();
        JsonArray blocks = new JsonArray();
        for (Cell c : cells) {
            int i = index.computeIfAbsent(c.data, k -> index.size());
            JsonArray arr = new JsonArray();
            arr.add(c.lx - loX);
            arr.add(c.ly);
            arr.add(c.lz - loZ);
            arr.add(i);
            blocks.add(arr);
        }
        JsonArray palette = new JsonArray();
        index.keySet().forEach(palette::add);
        JsonArray size = new JsonArray();
        size.add(hiX - loX + 1);
        size.add(maxY - minY + 1);
        size.add(hiZ - loZ + 1);

        JsonObject out = new JsonObject();
        out.add("size", size);
        out.add("palette", palette);
        out.add("blocks", blocks);
        return out;
    }
}
