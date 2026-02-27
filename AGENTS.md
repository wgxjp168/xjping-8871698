# AGENTS.md

## Cursor Cloud specific instructions

This repository contains a Maven-based Java project (`hello-app`).

### Environment

- **Java**: OpenJDK 21 (pre-installed at `/usr/lib/jvm/java-21-openjdk-amd64`)
- **Maven**: 3.9.6 (installed at `/opt/apache-maven-3.9.6`, symlinked to `/usr/local/bin/mvn`)
- `MAVEN_HOME` and `PATH` are configured in `~/.bashrc`

### Common commands

All commands run from `/workspace/hello-app`:

- **Compile**: `mvn compile`
- **Test**: `mvn test`
- **Package**: `mvn package`
- **Run**: `java -cp target/hello-app-1.0-SNAPSHOT.jar com.example.App`

### Notes

- The `pom.xml` targets Java 17 compiler release (`maven.compiler.release=17`) but runs on JDK 21, which is forward-compatible.
- Maven dependencies are cached in `~/.m2/repository`; first build downloads all plugins/deps from Maven Central.
