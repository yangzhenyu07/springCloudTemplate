# AGENTS.md

## Build & Run

```bash
# Full build (install modules to local repo first - required because modules depend on each other)
mvn clean install

# Build only yzy-demo (after parent modules are installed)
mvn clean package -pl yzy-demo

# Run the app
java -jar yzy-demo/target/yzy-demo-1.0-SNAPSHOT.jar

# Run with specific profile
java -jar yzy-demo/target/yzy-demo-1.0-SNAPSHOT.jar --spring.profiles.active=yzy
```

No Maven wrapper (`mvnw`) exists. Maven must be installed on the system.

## Module Structure

| Module | GroupId | Purpose |
|--------|---------|---------|
| `yzy-dependencies-bom` | com.example | Parent BOM - manages all dependency versions |
| `redis-module` | org.example.redis | Redis config beans (Jedis, Sentinel, Cluster support) |
| `common-module-v1` | com.example.common | Redis number tools + conditional bean loading |
| `common-module-v2` | com.example.common | Slimmer copy of v1 (no service layer) |
| `yzy-demo` | com.example | **Runnable Spring Boot app** - only module with `spring-boot-maven-plugin` |

Dependency chain: `yzy-demo` → `common-module-v1` → `redis-module`

## Key Facts

- **Java 17**, **Spring Boot 2.6.15**
- App runs on port **8088** (config in `application-yzy.yml`)
- Circular references are enabled (`allow-circular-references: true`) - this is intentional for Spring Boot 2.6+
- Redis is required at `127.0.0.1:6379` - the app initializes Redis lists on startup via `InitController`
- API docs via Knife4j/Springfox at `/doc.html`
- No test files exist in the repo

## Build Gotchas

- `redis-module` and `common-module-v1`/`v2` must be `mvn install`ed to local repo before `yzy-demo` can resolve them - a plain `mvn compile` on yzy-demo alone will fail
- Redis bean configs use `@ConditionalOnExpression("${spring.redis.my.flag:false} == true")` - if the flag is missing or false, Redis beans won't load
- `common-module-v1` uses `@Conditional(MyRedisConditional.class)` for its service beans

## Code Conventions

From `yzy.md`:
- 4-space indentation, 120 char line limit
- PascalCase classes, camelCase methods/variables
- Class and method Javadoc required
- Max 50 lines per method, 500 lines per class, 3 levels nesting

## Redis Key Constants

Defined in `RedsCondition` interface (`common-module-v1` and `common-module-v2`):
- `MESSAGE_IDENTIFIER_KEY` - 14-digit message ID
- `WALLET_ID_KEY` - 11-digit wallet ID
- `COMPREHENSIVE_SERIAL_NUMBER_KEY` - 7-digit serial
- `TRANSACTION_CENTER_SERIAL_NUMBER_OTHER_KEY` - 7-digit serial
- `TRANSACTION_CENTER_SERIAL_NUMBER_KEY` - 7-digit serial
- `CASE_NUMBER_KEY` - 9-digit business tracking code
