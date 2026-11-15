plugins {
    java
}

group = "dev.blueprint"
version = "1.0.0"

repositories {
    mavenCentral()
    maven("https://repo.papermc.io/repository/maven-public/")
}

dependencies {
    // 대상 서버: Paper 26.3 (다른 버전은 명시적으로 요청할 때만 변경)
    compileOnly("io.papermc.paper:paper-api:26.3.build.249-stable")
}

tasks.withType<JavaCompile> {
    options.encoding = "UTF-8"
    options.release.set(25)
}

tasks.processResources {
    val pluginVersion = project.version.toString()
    inputs.property("version", pluginVersion)
    filteringCharset = "UTF-8"
    filesMatching("plugin.yml") {
        expand("version" to pluginVersion)
    }
}

tasks.jar {
    archiveFileName.set("BlueprintBuilder-${project.version}.jar")
}
