package dev.blueprint.builder;

import org.bukkit.block.BlockFace;
import org.bukkit.block.structure.StructureRotation;

/**
 * 템플릿 좌표계 ↔ 월드 좌표계 변환.
 *
 * <p>템플릿 규칙: 정면(입구)은 z = 0 쪽이고 북쪽(-z)을 바라본다.
 * 플레이어가 바라보는 방향(forward)으로 템플릿의 +z 를 놓으면, 정면이 플레이어 쪽을 향하게 된다.
 * 남쪽을 바라볼 때가 회전 없음(identity)이다.
 */
public enum Orientation {
    SOUTH(0, 1, 1, 0, StructureRotation.NONE),
    WEST(-1, 0, 0, 1, StructureRotation.CLOCKWISE_90),
    NORTH(0, -1, -1, 0, StructureRotation.CLOCKWISE_180),
    EAST(1, 0, 0, -1, StructureRotation.COUNTERCLOCKWISE_90);

    /** 템플릿 +z 방향이 놓이는 월드 방향 (플레이어 정면). */
    public final int fx, fz;
    /** 템플릿 +x 방향이 놓이는 월드 방향. */
    public final int rx, rz;
    /** 템플릿 → 월드로 놓을 때 블록 데이터에 적용할 회전. */
    public final StructureRotation rotation;

    Orientation(int fx, int fz, int rx, int rz, StructureRotation rotation) {
        this.fx = fx;
        this.fz = fz;
        this.rx = rx;
        this.rz = rz;
        this.rotation = rotation;
    }

    /** 월드 → 템플릿 방향으로 블록 데이터를 되돌릴 때 쓰는 회전. */
    public StructureRotation inverse() {
        return switch (rotation) {
            case CLOCKWISE_90 -> StructureRotation.COUNTERCLOCKWISE_90;
            case COUNTERCLOCKWISE_90 -> StructureRotation.CLOCKWISE_90;
            default -> rotation;
        };
    }

    /** 템플릿 (lx, lz) → 월드 기준 오프셋 x */
    public int worldX(int lx, int lz) {
        return rx * lx + fx * lz;
    }

    public int worldZ(int lx, int lz) {
        return rz * lx + fz * lz;
    }

    /** 월드 오프셋 (dx, dz) → 템플릿 x */
    public int localX(int dx, int dz) {
        return rx * dx + rz * dz;
    }

    public int localZ(int dx, int dz) {
        return fx * dx + fz * dz;
    }

    public static Orientation of(BlockFace facing) {
        return switch (facing) {
            case NORTH -> NORTH;
            case EAST -> EAST;
            case WEST -> WEST;
            default -> SOUTH;
        };
    }
}
