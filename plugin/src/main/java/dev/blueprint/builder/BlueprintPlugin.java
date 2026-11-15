package dev.blueprint.builder;

import org.bukkit.command.PluginCommand;
import org.bukkit.plugin.java.JavaPlugin;

public final class BlueprintPlugin extends JavaPlugin {

    private ApiClient api;
    private BuildManager builds;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        builds = new BuildManager(this);
        reload();
        PluginCommand cmd = getCommand("tb");
        BlueprintCommand executor = new BlueprintCommand(this);
        cmd.setExecutor(executor);
        cmd.setTabCompleter(executor);
    }

    @Override
    public void onDisable() {
        if (builds != null) builds.shutdown();
    }

    void reload() {
        reloadConfig();
        String url = getConfig().getString("api-url", "http://127.0.0.1:5000");
        String key = getConfig().getString("api-key", "");
        String envKey = System.getenv("BLUEPRINT_API_KEY");
        if (envKey != null && !envKey.isBlank()) key = envKey;
        api = new ApiClient(url.trim(), key.trim());
        String problem = api.configProblem();
        if (problem != null) {
            getLogger().warning(problem + " 웹사이트 web/instance/plugin_api_key.txt 값을 넣고 /tb reload 하세요.");
        }
        getLogger().info("웹사이트 주소: " + url);
    }

    public ApiClient api() {
        return api;
    }

    public BuildManager builds() {
        return builds;
    }
}
