package com.example.bdemo.generator;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.generator.FastAutoGenerator;
import com.baomidou.mybatisplus.generator.config.OutputFile;
import com.baomidou.mybatisplus.generator.engine.VelocityTemplateEngine;

import java.io.File;
import java.net.URL;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * MyBatis-Plus 代码生成器入口
 *
 * <p>职责：读取 YZY_DB 中的配置类表结构，批量生成 Entity / Mapper / Service / ServiceImpl / Controller
 * 以及 Mapper XML，输出到 yzy-b-demo 模块的 src/main 目录。
 *
 * <p>为什么放在 src/test/java：
 * <ul>
 *   <li>生成器依赖（mybatis-plus-generator、velocity-engine-core）均为 test scope，不会被打进运行 jar；</li>
 *   <li>与主应用启动无关，不会被 @SpringBootApplication 扫描到。</li>
 * </ul>
 *
 * <p>运行方式（在仓库根目录执行，注意 -Dexec.classpathScope=test 必须带，否则 test scope 依赖不在类路径上）：
 * <pre>
 *   E:/apache-maven-3.6.3/bin/mvn.cmd -q -pl yzy-b-demo -am -DskipTests install
 *   E:/apache-maven-3.6.3/bin/mvn.cmd -pl yzy-b-demo test-compile \
 *       org.codehaus.mojo:exec-maven-plugin:3.1.0:java \
 *       -Dexec.classpathScope=test \
 *       -Dexec.mainClass=com.example.bdemo.generator.CodeGenerator
 * </pre>
 *
 * <p>可选 JVM 参数：
 * <ul>
 *   <li>-Dgen.module.dir=E:/work/springCloudTemplate/yzy-b-demo —— 手动指定模块根目录（默认从 classpath 推导）</li>
 *   <li>-Dgen.tables=flow_info,flow_node —— 只生成指定表（默认生成 TABLES 常量中的全部表）</li>
 *   <li>-Dgen.file.override=false —— 是否覆盖同名文件（默认 false，避免覆盖已手改过的代码）</li>
 * </ul>
 *
 * @author yzy
 * @version 1.0
 */
public class CodeGenerator {

    /**
     * 数据库连接地址
     * useInformationSchema=true 与 remarks=true 用于让 JDBC 驱动读到表和字段的 COMMENT（生成中文注释依赖它）
     */
    private static final String JDBC_URL = "jdbc:mysql://127.0.0.1:3306/YZY_DB"
            + "?useUnicode=true&characterEncoding=utf8&useSSL=false&allowPublicKeyRetrieval=true"
            + "&serverTimezone=UTC&useInformationSchema=true&remarks=true";

    /**
     * 数据库账号
     */
    private static final String USERNAME = "YZY_MASTER";

    /**
     * 数据库密码
     */
    private static final String PASSWORD = "yzy@1234";

    /**
     * 默认需要生成的表（流程编排相关配置表）
     */
    private static final List<String> TABLES = Arrays.asList(
            "flow_info",
            "flow_node_relation",
            "flow_node",
            "scene_info",
            "scene_flow_relation",
            "trade_config"
    );

    /**
     * 父包名
     */
    private static final String PARENT_PACKAGE = "com.example.bdemo";

    /**
     * 作者名，写入生成类的 Javadoc
     */
    private static final String AUTHOR = "yzy";

    /**
     * 代码块：main 入口
     *
     * @param args 运行参数（不使用，配置通过 JVM 参数调整）
     */
    public static void main(String[] args) {
        // 模块根目录由 classpath 推导而来，避免写死绝对路径导致换机器失效
        String moduleDir = resolveModuleDir();
        String javaDir = moduleDir + "/src/main/java";
        String xmlDir = moduleDir + "/src/main/resources/mapper";

        List<String> tables = resolveTables();
        System.out.println("=== MyBatis-Plus Code Generator ===");
        System.out.println("module dir   : " + moduleDir);
        System.out.println("output java  : " + javaDir);
        System.out.println("output xml   : " + xmlDir);
        System.out.println("tables       : " + tables);

        FastAutoGenerator.create(JDBC_URL, USERNAME, PASSWORD)
                // 全局配置
                .globalConfig(builder -> {
                    builder.author(AUTHOR)
                            .outputDir(javaDir)
                            // 只到天，避免同一天重复生成时 @since 行产生无意义的代码差异
                            .commentDate("yyyy-MM-dd")
                            // 生成后不弹出文件管理器（服务器上会阻塞）
                            .disableOpenDir();
                            // 默认不覆盖已有文件，避免覆盖人工修改过的代码；需要时加 -Dgen.file.override=true
                            if (Boolean.parseBoolean(System.getProperty("gen.file.override", "false"))) {
                                builder.fileOverride();
                            }
                })
                // 包配置
                .packageConfig(builder -> {
                    builder.parent(PARENT_PACKAGE)
                            .entity("entity")
                            .mapper("mapper")
                            .service("service")
                            .serviceImpl("service.impl")
                            .controller("controller")
                            // Mapper XML 单独输出到 resources/mapper
                            .pathInfo(Collections.singletonMap(OutputFile.xml, xmlDir));
                })
                // 策略配置
                .strategyConfig(builder -> {
                    builder.addInclude(tables)
                            // 实体策略：Lombok + 主键自增
                            .entityBuilder()
                            .enableLombok()
                            .idType(IdType.AUTO)
                            // 与项目现有风格一致：服务接口不加 I 前缀，例如 SysUserService
                            .serviceBuilder()
                            .formatServiceFileName("%sService")
                            // Mapper 打上 @Mapper，配合启动类 @MapperScan 双重保险
                            .mapperBuilder()
                            .enableMapperAnnotation()
                            // Controller 使用 @RestController + @RequestMapping
                            .controllerBuilder()
                            .enableRestStyle();
                })
                // Velocity 是 MP Generator 的默认模板引擎，显式声明避免歧义
                .templateEngine(new VelocityTemplateEngine())
                .execute();

        System.out.println("=== Code generator finished ===");
        // MySQL 驱动会开一个守护清理线程，命令行跑完不主动退出会拖到 exec:java 超时告警
        System.exit(0);
    }

    /**
     * 解析模块根目录
     *
     * <p>优先读取 JVM 参数 -Dgen.module.dir；未指定时从当前 classpath 推导：
     * classpath 根为 yzy-b-demo/target/test-classes，向上两级即为模块根目录。
     *
     * @return 模块根目录绝对路径
     */
    private static String resolveModuleDir() {
        String manual = System.getProperty("gen.module.dir");
        if (manual != null && !manual.isEmpty()) {
            return new File(manual).getAbsolutePath();
        }
        try {
            URL classpathRoot = CodeGenerator.class.getResource("/");
            if (classpathRoot == null) {
                throw new IllegalStateException("无法定位 classpath 根目录");
            }
            File classesDir = new File(classpathRoot.toURI());
            File targetDir = classesDir.getParentFile();
            File moduleDir = targetDir.getParentFile();
            return moduleDir.getAbsolutePath();
        } catch (Exception e) {
            throw new IllegalStateException("推导模块目录失败，请通过 -Dgen.module.dir 显式指定", e);
        }
    }

    /**
     * 解析本次需要生成的表清单
     *
     * @return 表名列表
     */
    private static List<String> resolveTables() {
        String tables = System.getProperty("gen.tables");
        if (tables == null || tables.isEmpty()) {
            return TABLES;
        }
        return Arrays.asList(tables.split(","));
    }
}
