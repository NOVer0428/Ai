package dev.blueprint.builder;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.minimessage.MiniMessage;

final class Text {
    private Text() {}

    static String escape(String s) {
        return MiniMessage.miniMessage().escapeTags(s);
    }

    static Component mini(String s) {
        return MiniMessage.miniMessage().deserialize(s);
    }
}
