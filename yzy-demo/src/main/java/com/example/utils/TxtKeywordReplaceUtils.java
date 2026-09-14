package com.example.utils;

import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.Objects;

/**
 * 文本文件多关键字批量替换工具类
 *
 * 场景说明：
 * 对 txt 等文本文件做「多个关键字 -> 替换值」的占位符填充或内容订正。
 * 例如：把模板文件里的 ${name}、${date} 等占位符批量替换成真实内容。
 *
 * 实现说明：
 * 1. 读取文件全部内容为字符串（保留原始换行符，不做逐行处理，避免行拼接丢失 \r\n）；
 * 2. 遍历传入的 Map，用 for 循环逐个执行 String.replace（字面量替换，非正则，无需转义）；
 * 3. 统计每个关键字实际命中的次数并累加返回；
 * 4. 将替换后的内容写回目标文件。
 *
 * 注意事项：
 * 1. 编码：txt 文件编码不确定时请显式传 charset（如 GBK），默认 UTF-8；
 * 2. 顺序：Map 迭代顺序不定，若替换值本身又包含其它待替换关键字，结果依赖迭代顺序，请自行保证；
 * 3. null 值：某个 key 对应的 value 为 null 时，视为将该关键字替换为空串（删除占位符）；
 * 4. 大文件：本工具一次性读入内存，适合 MB 级以下文本，超大文件建议逐行流式处理；
 * 5. 兼容性：仅使用 JDK 7/8 提供的 API（Files.readAllBytes / Files.write / getBytes），
 *    可直接用于编译目标为 Java 8（source/target 1.8）的项目。
 */
public final class TxtKeywordReplaceUtils {

    // =====================================================
    // 常量定义
    // =====================================================

    /**
     * 默认字符集
     * 说明：UTF-8 是 Linux / 大多数现代 txt 文件的默认编码
     */
    private static final Charset DEFAULT_CHARSET = StandardCharsets.UTF_8;

    private TxtKeywordReplaceUtils() {
        throw new AssertionError("工具类不可实例化");
    }

    // =====================================================
    // 公共 API：覆盖写回原文件
    // =====================================================

    /**
     * 替换文件中的多个关键字，覆盖写回原文件（默认 UTF-8 编码）
     * 场景说明：
     * 最常见的用法：传入文件路径和「关键字 -> 替换值」的 Map，方法返回实际替换总次数
     * 例如：replaceFile("E:/tmp/template.txt", map) 会把文件中命中的关键字全部替换并写回
     *
     * @param filePath   待处理 txt 文件路径
     * @param keywordMap 关键字映射（key：原关键字，value：替换值，null 视为删除该关键字）
     * @return 实际替换总次数（全部关键字的命中次数之和）
     * @throws IOException              文件不存在或读写失败
     * @throws IllegalArgumentException 文件路径或关键字 Map 为空、含空关键字
     */
    public static int replaceFile(String filePath, Map<String, String> keywordMap)
            throws IOException {

        return replaceFile(filePath, DEFAULT_CHARSET, keywordMap);
    }

    /**
     * 替换文件中的多个关键字，覆盖写回原文件（自定义编码）
     * 场景说明：
     * 文本文件编码不一定是 UTF-8（如 Windows 记事本默认 GBK），需要显式指定字符集
     * 例如：replaceFile("E:/tmp/old.txt", "GBK", map) 按 GBK 读取并写回
     *
     * @param filePath   待处理 txt 文件路径
     * @param charset    文件字符集名称（如 "UTF-8"、"GBK"）
     * @param keywordMap 关键字映射（key：原关键字，value：替换值，null 视为删除该关键字）
     * @return 实际替换总次数（全部关键字的命中次数之和）
     * @throws IOException              文件不存在或读写失败
     * @throws IllegalArgumentException 参数不合法或字符集不支持
     */
    public static int replaceFile(String filePath, String charset, Map<String, String> keywordMap)
            throws IOException {

        return replaceFile(filePath, Charset.forName(charset), keywordMap);
    }

    /**
     * 替换文件中的多个关键字，覆盖写回原文件（Charset 重载，内部实现）
     *
     * @param filePath   待处理 txt 文件路径
     * @param charset    文件字符集
     * @param keywordMap 关键字映射（key：原关键字，value：替换值，null 视为删除该关键字）
     * @return 实际替换总次数
     * @throws IOException              文件不存在或读写失败
     * @throws IllegalArgumentException 参数不合法
     */
    public static int replaceFile(String filePath, Charset charset, Map<String, String> keywordMap)
            throws IOException {

        // 校验输入，避免后续出现难排查的空指针或静默错误
        Objects.requireNonNull(charset, "字符集不能为空");
        Path path = Paths.get(Objects.requireNonNull(filePath, "文件路径不能为空"));
        validateKeywordMap(keywordMap);

        // 读取文件全部内容（原样保留 \r\n 等换行符；readAllBytes 为 JDK 7 API，兼容 Java 8）
        String content = new String(Files.readAllBytes(path), charset);
        // for 循环逐个关键字替换，返回本次处理的总替换次数
        int total = replaceByLoop(content, keywordMap, path, charset);
        return total;
    }

    // =====================================================
    // 公共 API：输出到新文件（保留原文件）
    // =====================================================

    /**
     * 替换文件中的多个关键字，输出到新文件（原文件保持不变）
     * 场景说明：
     * 需要保留原件、把替换结果另存为副本时使用
     * 例如：replaceTo("E:/tmp/src.txt", "E:/tmp/dst.txt", "UTF-8", map)
     *
     * @param sourcePath 源文件路径（只读，不会被修改）
     * @param targetPath 目标文件路径（不存在则自动创建，存在则覆盖）
     * @param charset    文件字符集名称（如 "UTF-8"、"GBK"）
     * @param keywordMap 关键字映射（key：原关键字，value：替换值，null 视为删除该关键字）
     * @return 实际替换总次数
     * @throws IOException              文件不存在或读写失败
     * @throws IllegalArgumentException 参数不合法或字符集不支持
     */
    public static int replaceTo(
            String sourcePath,
            String targetPath,
            String charset,
            Map<String, String> keywordMap) throws IOException {

        Objects.requireNonNull(sourcePath, "源文件路径不能为空");
        Objects.requireNonNull(targetPath, "目标文件路径不能为空");
        validateKeywordMap(keywordMap);
        Charset cs = Charset.forName(charset);

        Path src = Paths.get(sourcePath);
        Path target = Paths.get(targetPath);
        String content = new String(Files.readAllBytes(src), cs);
        return replaceByLoop(content, keywordMap, target, cs);
    }

    // =====================================================
    // 私有方法
    // =====================================================

    /**
     * for 循环执行关键字替换并写回目标文件
     * 核心逻辑说明：
     * 1. 遍历 Map 中每个 entry，取出关键字与替换值；
     * 2. 统计该关键字在内容中的出现次数并累加；
     * 3. 命中次数大于 0 才执行 String.replace（字面量替换，关键字含 $ . * 等正则字符也无需转义）；
     * 4. 全部替换完成后一次性写回文件，避免多次磁盘 IO。
     *
     * @param content    文件原始内容
     * @param keywordMap 关键字映射
     * @param targetPath 写入目标路径
     * @param charset    写回时使用的字符集
     * @return 实际替换总次数
     * @throws IOException 写入失败
     */
    private static int replaceByLoop(
            String content,
            Map<String, String> keywordMap,
            Path targetPath,
            Charset charset) throws IOException {

        String replaced = content;
        int total = 0;
        for (Map.Entry<String, String> entry : keywordMap.entrySet()) {
            String keyword = entry.getKey();
            // null 值语义：等价于把该关键字替换为空串（删除占位符）
            String value = entry.getValue() == null ? "" : entry.getValue();

            int count = countOccurrences(replaced, keyword);
            if (count > 0) {
                replaced = replaced.replace(keyword, value);
                total += count;
            }
        }
        // getBytes + Files.write 为 JDK 7 API，兼容 Java 8
        Files.write(targetPath, replaced.getBytes(charset));
        return total;
    }

    /**
     * 统计某个关键字在文本中的出现次数（非重叠统计）
     * 实现说明：
     * 使用 indexOf 从当前位置向后查找并移动游标，避免正则表达式匹配
     * 因此关键字包含 . $ [ ] 等字符时不会被当作正则元字符误解析
     *
     * @param text    被查找的文本
     * @param keyword 要统计的关键字
     * @return 出现次数，关键字为空时返回 0
     */
    private static int countOccurrences(String text, String keyword) {
        if (keyword.isEmpty()) {
            return 0;
        }
        int count = 0;
        int index = 0;
        while ((index = text.indexOf(keyword, index)) != -1) {
            count++;
            index += keyword.length();
        }
        return count;
    }

    /**
     * 校验关键字 Map 合法性
     * 说明：
     * - Map 不能为 null 或空，否则替换无意义，直接抛出异常提示调用方
     * - key 不能为 null 或空字符串，空关键字会导致 indexOf 死循环或替换整个内容
     *
     * @param keywordMap 关键字映射
     * @throws IllegalArgumentException Map 为 null/空，或包含空关键字
     */
    private static void validateKeywordMap(Map<String, String> keywordMap) {
        if (keywordMap == null || keywordMap.isEmpty()) {
            throw new IllegalArgumentException("关键字映射不能为空");
        }
        for (String keyword : keywordMap.keySet()) {
            if (keyword == null || keyword.trim().isEmpty()) {
                throw new IllegalArgumentException("关键字不能为 null 或空字符串");
            }
        }
    }

}
