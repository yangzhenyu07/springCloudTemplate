package com.example.utils;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.math.RoundingMode;
import java.text.DecimalFormat;
import java.util.Collection;
import java.util.Objects;

/**
 * 企业级金额工具类
 *
 */
public  class MoneyUtils {

    // =====================================================
    // 常量定义
    // =====================================================

    /**
     * 常用的默认舍入模式
     * HALF_UP 是最常见的商业舍入模式（四舍五入），符合大多数财务场景的预期
     */
    public static final RoundingMode DEFAULT_ROUND = RoundingMode.HALF_UP;

    /**
     * Token 相关的舍入模式
     * DOWN 是向下舍入，适合需要严格控制精度的 Token 场景，避免意外增大金额
     */
    public static final RoundingMode TOKEN_ROUND = RoundingMode.DOWN;

    /**
     * BigInteger 零值常量（避免重复创建）
     */
    private static final BigInteger ZERO_BIG_INTEGER = BigInteger.ZERO;

    /**
     * DecimalFormat 线程本地缓存
     * 作用：避免重复创建 DecimalFormat 实例，提升性能；确保线程安全
     */
    private static final ThreadLocal<DecimalFormatHelper> DECIMAL_FORMAT_CACHE =
            ThreadLocal.withInitial(DecimalFormatHelper::new);

    private MoneyUtils() {
        throw new AssertionError("工具类不可实例化");
    }

    // =====================================================
    // DecimalFormat 辅助类（确保正确的 remove 逻辑）
    // =====================================================

    private static class DecimalFormatHelper {

        /**
         * 每个线程独享一个 DecimalFormat 实例
         * 作用：避免线程安全问题
         * 说明：构造时不设置任何特定格式，使用时动态调整格式
         */
        private final DecimalFormat format = new DecimalFormat();

        DecimalFormat getFormat() {
            return format;
        }

        /**
         * 使用完毕后重置状态
         * 作用：确保下次使用时不会受到上次设置的影响
         */
        void reset() {
            // 重置到默认状态（可选，取决于下次使用）
            format.setGroupingUsed(false);
        }
    }

    // =====================================================
    // 法币枚举
    // =====================================================

    /**
     * 法币类型枚举
     * 说明：
     * - 小数位数：不同货币可能有不同的小数位要求
     * - 货币符号：可用于格式化输出
     * - 舍入模式：不同货币可能有不同的舍入需求，默认使用 HALF_UP
     */
    public enum Currency {
        // 人民币, 2位小数 , 默认舍入模式 HALF_UP
        CNY(2, "¥", RoundingMode.HALF_UP),
        // 美元, 2位小数, 默认舍入模式 HALF_UP
        USD(2, "$", RoundingMode.HALF_UP),
        // 欧元, 2位小数, 默认舍入模式 HALF_UP
        EUR(2, "€", RoundingMode.HALF_UP),
        // 日元, 0位小数（不使用小数部分）, 默认舍入模式 HALF_UP
        JPY(0, "¥", RoundingMode.HALF_UP);

        private final int scale;
        private final String symbol;
        private final RoundingMode rounding;

        Currency(int scale, String symbol, RoundingMode rounding) {
            this.scale = scale;
            this.symbol = symbol;
            this.rounding = rounding;
        }

        public int getScale() {
            return scale;
        }

        public String getSymbol() {
            return symbol;
        }

        public RoundingMode getRounding() {
            return rounding;
        }
    }

    // =====================================================
    // Token 枚举
    // =====================================================

    /**
     * Token 类型枚举
     * 说明：
     * - decimals：小数位数（由链协议定义，不同 Token 有不同的 decimals）
     * - rounding：舍入模式，全部使用 DOWN（避免意外增大）
     * 原因：高精度计算中的意外增大会导致严重的财务问题
     */
    public enum Token {
        // 以太坊, 18位小数, 舍入模式 DOWN（避免意外增大）
        ETH(18, RoundingMode.DOWN),
        // 比特币, 8位小数, 舍入模式 DOWN（避免意外增大）
        BTC(8, RoundingMode.DOWN),
        // 稳定币通常使用 6 位小数，舍入模式 DOWN（避免意外增大）
        USDT(6, RoundingMode.DOWN),
        // USDC 也是 6 位小数，舍入模式 DOWN（避免意外增大）
        USDC(6, RoundingMode.DOWN),
        // BNB 也是 18 位小数，舍入模式 DOWN（避免意外增大）
        BNB(18, RoundingMode.DOWN);

        private final int decimals;
        private final RoundingMode rounding;

        Token(int decimals, RoundingMode rounding) {
            this.decimals = decimals;
            this.rounding = rounding;
        }

        public int getDecimals() {
            return decimals;
        }

        public RoundingMode getRounding() {
            return rounding;
        }
    }

    // =====================================================
    // 构造与转换
    // =====================================================

    /**
     * 从字符串构造 BigDecimal
     * 增强输入验证，支持逗号分隔，禁止科学计数法输入，避免精度问题和意外结果
     *
     * @param value 金额字符串
     * @return BigDecimal 金额对象
     * @throws IllegalArgumentException 如果输入格式无效
     */
    public static BigDecimal of(String value) {
        // 检查 value 不能为 null，然后去掉前后空格
        String clean = Objects.requireNonNull(value, "金额不能为空").trim();
        if (clean.isEmpty()) {
            throw new IllegalArgumentException("金额不能为空字符串");
        }

        // 移除逗号，准备转换为 BigDecimal
        clean = clean.replace(",", "");

        // 禁止科学计数法输入，避免精度问题和意外结果
        // 检查金额里有没有出现科学计数法（比如 1E6、1.23e8）
        if (clean.contains("E") || clean.contains("e")) {
            throw new IllegalArgumentException("金额不支持科学计数法: " + value);
        }

        try {
            return new BigDecimal(clean);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("非法的金额格式: " + value, e);
        }
    }

    /**
     * 直接从 long 创建 BigDecimal
     * 作用：避免使用 new BigDecimal(double) 导致的精度问题
     */
    public static BigDecimal of(long value) {
        return BigDecimal.valueOf(value);
    }

    /**
     * 直接从 double 创建 BigDecimal
     * 方式：先转为字符串，然后创建，避免 double 精度问题
     */
    public static BigDecimal of(double value) {
        return new BigDecimal(Double.toString(value));
    }

    // =====================================================
    // 四则运算（基础版）
    // =====================================================

    /**
     * 加法方法
     * 增加 null 检查，避免潜在的 NullPointerException
     */
    public static BigDecimal add(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.add(b);
    }

    /**
     * 减法方法
     * 增加 null 检查，避免潜在的 NullPointerException
     */
    public static BigDecimal subtract(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.subtract(b);
    }

    /**
     * 乘法方法
     * 增加 null 检查，避免潜在的 NullPointerException
     *
     * 场景说明：
     * 纯粹的乘法计算，结果不需要立即舍入的场景
     * 例如：计算数量 * 单价得到金额，或者计算金额 * 汇率得到转换后的金额等场景
     * 这些场景通常允许中间结果保留更多小数位，以避免过早舍入导致的精度损失
     */
    public static BigDecimal multiply(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.multiply(b);
    }

    /**
     * 除法方法
     * 增加 null 检查，避免潜在的 NullPointerException
     *
     * 场景说明：
     * 纯粹的除法计算，结果不需要立即舍入的场景
     * 例如：计算总金额 / 数量得到单价，或者计算金额 / 汇率得到转换后的金额等场景
     * 这些场景通常允许中间结果保留更多小数位，以避免过早舍入导致的精度损失
     *
     * @param a 被除数
     * @param b 除数
     * @param scale 小数位数
     * @param roundingMode 舍入模式
     * @throws IllegalArgumentException 如果除数为 0 或参数无效
     */
    public static BigDecimal divide(
            BigDecimal a,
            BigDecimal b,
            int scale,
            RoundingMode roundingMode) {

        checkNotNull(a, b);
        Objects.requireNonNull(roundingMode, "舍入模式不能为空");
        if (scale < 0) {
            throw new IllegalArgumentException("scale 不能小于 0");
        }
        if (eqZero(b)) {
            throw new IllegalArgumentException("除数不能为 0");
        }
        return a.divide(b, scale, roundingMode);
    }

    /**
     * 乘法并舍入方法
     * 增加 null 检查，避免潜在的 NullPointerException
     *
     * 场景说明：
     * 乘法后需要立即舍入的场景，避免中间结果过大导致的精度问题
     * 例如：计算金额 * 百分比，或者金额 * 汇率等场景
     * 通常需要在乘法后立即进行舍入，以符合业务需求和财务规范
     *
     * @param a 第一个乘数
     * @param b 第二个乘数
     * @param scale 舍入小数位数
     * @param roundingMode 舍入模式
     */
    public static BigDecimal multiply(
            BigDecimal a,
            BigDecimal b,
            int scale,
            RoundingMode roundingMode) {

        checkNotNull(a, b);
        Objects.requireNonNull(roundingMode, "舍入模式不能为空");
        if (scale < 0) {
            throw new IllegalArgumentException("scale 不能小于 0");
        }
        // 先乘法后舍入，避免中间结果过大导致的精度问题
        return a.multiply(b).setScale(scale, roundingMode);
    }

    /**
     * 除法（带零值保护）
     * 增加 null 检查，避免潜在的 NullPointerException
     *
     * 场景说明：
     * 除法后需要立即舍入的场景，避免中间结果过大导致的精度问题
     * 如果分母为 0，直接返回 0，避免异常
     * 例如：计算金额 / 数量得到单价，或者金额 / 汇率得到转换后的金额等场景
     * 通常需要在除法后立即进行舍入，以符合业务需求和财务规范
     *
     * @param a 被除数
     * @param b 除数
     * @param scale 舍入小数位数
     * @param roundingMode 舍入模式
     * @return 除法结果，如果 b 为 0 则返回 0
     */
    public static BigDecimal divideOrZero(
            BigDecimal a,
            BigDecimal b,
            int scale,
            RoundingMode roundingMode) {

        checkNotNull(a, b);
        if (eqZero(b)) {
            return BigDecimal.ZERO;
        }
        return divide(a, b, scale, roundingMode);
    }

    // =====================================================
    // 四则运算（法币便捷版）
    // =====================================================

    /**
     * 法币加法方法
     * 场景说明：
     * 法币金额的加减乘除，自动使用对应货币的默认小数位和舍入模式，简化调用
     * 避免每次都需要传入 scale 和 roundingMode 参数
     *
     * @param a 第一个加数
     * @param b 第二个加数
     * @param currency 货币类型
     * @return 加法结果，按货币规则舍入
     */
    public static BigDecimal add(BigDecimal a, BigDecimal b, Currency currency) {
        checkNotNull(a, b);
        Objects.requireNonNull(currency, "货币类型不能为空");
        return roundMoney(a.add(b), currency);
    }

    /**
     * 法币减法方法
     * 场景说明：
     * 法币金额的减法，自动使用对应货币的默认小数位和舍入模式，简化调用
     * 避免每次都需要传入 scale 和 roundingMode 参数
     *
     * @param a 被减数
     * @param b 减数
     * @param currency 货币类型
     * @return 减法结果，按货币规则舍入
     */
    public static BigDecimal subtract(BigDecimal a, BigDecimal b, Currency currency) {
        checkNotNull(a, b);
        Objects.requireNonNull(currency, "货币类型不能为空");
        return roundMoney(a.subtract(b), currency);
    }

    /**
     * 法币乘法方法
     * 场景说明：
     * 法币金额的乘法，自动使用对应货币的默认小数位和舍入模式，简化调用
     * 避免每次都需要传入 scale 和 roundingMode 参数
     *
     * @param a 第一个乘数
     * @param b 第二个乘数
     * @param currency 货币类型
     * @return 乘法结果，按货币规则舍入
     */
    public static BigDecimal multiply(
            BigDecimal a,
            BigDecimal b,
            Currency currency) {

        checkNotNull(a, b);
        Objects.requireNonNull(currency, "货币类型不能为空");
        return multiply(a, b, currency.getScale(), currency.getRounding());
    }

    /**
     * 法币除法方法
     * 场景说明：
     * 法币金额的除法，自动使用对应货币的默认小数位和舍入模式，简化调用
     * 避免每次都需要传入 scale 和 roundingMode 参数
     *
     * @param a 被除数
     * @param b 除数
     * @param currency 货币类型
     * @return 除法结果，按货币规则舍入
     */
    public static BigDecimal divide(
            BigDecimal a,
            BigDecimal b,
            Currency currency) {

        checkNotNull(a, b);
        Objects.requireNonNull(currency, "货币类型不能为空");
        return divide(a, b, currency.getScale(), currency.getRounding());
    }

    // =====================================================
    // 批量聚合
    // =====================================================

    /**
     * BigDecimal 与 BigInteger 的区别说明：
     * - BigDecimal：适用于需要高精度的小数计算的场景，常用于法币金额的计算
     * - BigInteger：适用于需要处理非常大的整数的场景，常用于原始金额（如 Wei、Satoshi 等）的计算
     *
     * sum 与 sumRaw 的区别说明：
     * - sum 方法：针对 BigDecimal 的，适用于处理法币金额的求和场景
     * - sumRaw 方法：针对 BigInteger 的，适用于处理原始金额（如 Wei、Satoshi 等）的求和场景
     */

    /**
     * 批量金额求和
     * 场景说明：
     * 批量金额求和，自动处理 null 和空集合的情况，避免调用方需要额外的 null 检查
     * 例如：计算多个金额的总和，或者多个金额的总和与一个固定金额的比较等场景
     * 与 sumRaw 比较：sum 方法是针对 BigDecimal 的，而 sumRaw 方法是针对 BigInteger 的
     * 适用于处理法币金额的求和场景，自动处理 null 和空集合的情况，避免调用方需要额外的 null 检查
     *
     * @param values 金额集合（可包含 null 元素）
     * @return 总和，如果集合为空或全为 null 则返回 0
     */
    public static BigDecimal sum(Collection<BigDecimal> values) {
        if (values == null || values.isEmpty()) {
            return BigDecimal.ZERO;
        }
        // 使用流式 API 进行聚合，增加 null 过滤，避免潜在的 NullPointerException
        return values.stream()
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /**
     * 批量原始金额求和
     * 场景说明：
     * 批量原始金额求和，自动处理 null 和空集合的情况，避免调用方需要额外的 null 检查
     * 例如：计算多个金额的总和，或者多个金额的总和与一个固定金额的比较等场景
     * 和 sum 比较：sum 方法是针对 BigDecimal 的，而 sumRaw 方法是针对 BigInteger 的
     * 适用于处理原始金额（如 Wei、Satoshi 等）的求和场景
     *
     * @param amounts 金额集合（可包含 null 元素）
     * @return 总和，如果集合为空或全为 null 则返回 0
     */
    public static BigInteger sumRaw(Collection<BigInteger> amounts) {
        if (amounts == null || amounts.isEmpty()) {
            return ZERO_BIG_INTEGER;
        }
        // 使用流式 API 进行聚合，增加 null 过滤，避免潜在的 NullPointerException
        return amounts.stream()
                .filter(Objects::nonNull)
                .reduce(ZERO_BIG_INTEGER, BigInteger::add);
    }

    // =====================================================
    // 比较
    // =====================================================

    /**
     * 相等比较方法
     * 场景说明：
     * 金额比较，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：比较两个金额是否相等，或者比较一个金额与一个固定金额的大小关系等场景
     *
     * 实现说明：
     * return a.compareTo(b) == 0 表示 a 等于 b
     * return a.compareTo(b) > 0 表示 a 大于 b
     * return a.compareTo(b) < 0 表示 a 小于 b
     * 使用 compareTo 而不是 equals 来比较 BigDecimal 是否相等，避免 scale 不同导致的比较失败
     * 例如：1.0 和 1.00 在数值上是相等的，但如果直接使用 equals 方法比较会返回 false，因为它们的 scale 不同
     *
     * @param a 第一个数
     * @param b 第二个数
     * @return 如果 a == b 则返回 true
     */
    public static boolean eq(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.compareTo(b) == 0;
    }

    /**
     * 大于比较方法
     * 场景说明：
     * 金额不等比较，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：比较两个金额的大小关系，或者比较一个金额与一个固定金额的大小关系等场景
     *
     * 实现说明：
     * return a.compareTo(b) > 0 表示 a 大于 b
     * return a.compareTo(b) < 0 表示 a 小于 b
     * return a.compareTo(b) == 0 表示 a 等于 b
     * 使用 compareTo 而不是 equals 来比较 BigDecimal 是否大于，避免 scale 不同导致的比较失败
     * 例如：1.0 和 1.00 在数值上是相等的，但如果直接使用 equals 方法比较会返回 false，因为它们的 scale 不同
     *
     * @param a 第一个数
     * @param b 第二个数
     * @return 如果 a > b 则返回 true
     */
    public static boolean gt(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.compareTo(b) > 0;
    }

    /**
     * 大于等于比较方法
     * 场景说明：
     * 金额大于等于比较，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：比较一个金额是否大于等于另一个金额，或者比较一个金额与一个固定金额的大小关系等场景
     *
     * 实现说明：
     * return a.compareTo(b) > 0 表示 a 大于 b
     * return a.compareTo(b) < 0 表示 a 小于 b
     * return a.compareTo(b) == 0 表示 a 等于 b
     * 使用 compareTo 而不是 equals 来比较 BigDecimal 是否大于等于，避免 scale 不同导致的比较失败
     * 例如：1.0 和 1.00 在数值上是相等的，但如果直接使用 equals 方法比较会返回 false，因为它们的 scale 不同
     *
     * @param a 第一个数
     * @param b 第二个数
     * @return 如果 a >= b 则返回 true
     */
    public static boolean ge(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.compareTo(b) >= 0;
    }

    /**
     * 小于比较方法
     * 场景说明：
     * 金额小于比较，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：比较一个金额是否小于另一个金额，或者比较一个金额与一个固定金额的大小关系等场景
     *
     * 实现说明：
     * return a.compareTo(b) < 0 表示 a 小于 b
     * return a.compareTo(b) > 0 表示 a 大于 b
     * return a.compareTo(b) == 0 表示 a 等于 b
     * 使用 compareTo 而不是 equals 来比较 BigDecimal 是否小于，避免 scale 不同导致的比较失败
     * 例如：1.0 和 1.00 在数值上是相等的，但如果直接使用 equals 方法比较会返回 false，因为它们的 scale 不同
     *
     * @param a 第一个数
     * @param b 第二个数
     * @return 如果 a < b 则返回 true
     */
    public static boolean lt(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.compareTo(b) < 0;
    }

    /**
     * 小于等于比较方法
     * 场景说明：
     * 金额小于等于比较，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：比较一个金额是否小于等于另一个金额，或者比较一个金额与一个固定金额的大小关系等场景
     *
     * 实现说明：
     * return a.compareTo(b) < 0 表示 a 小于 b
     * 使用 compareTo 而不是 equals 来比较 BigDecimal 是否小于等于，避免 scale 不同导致的比较失败
     * 例如：1.0 和 1.00 在数值上是相等的，但如果直接使用 equals 方法比较会返回 false，因为它们的 scale 不同
     *
     * @param a 第一个数
     * @param b 第二个数
     * @return 如果 a <= b 则返回 true
     */
    public static boolean le(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.compareTo(b) <= 0;
    }

    // =====================================================
    // 与 0 比较
    // =====================================================

    /**
     * 判断金额是否大于 0
     * 场景说明：
     * 判断金额是否大于 0，注意使用 compareTo 而不是 equals 来比较 BigDecimal 是否大于 0
     * 避免 scale 不同导致的比较失败
     *
     * @param amount 金额
     * @return 如果 amount > 0 则返回 true
     */
    public static boolean gtZero(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        // 使用 compareTo 而不是 equals 来比较 BigDecimal 是否大于 0，避免 scale 不同导致的比较失败
        return amount.compareTo(BigDecimal.ZERO) > 0;
    }

    /**
     * 判断金额是否大于等于 0
     * 场景说明：
     * 判断金额是否大于等于 0，注意使用 compareTo 而不是 equals 来比较 BigDecimal 是否大于等于 0
     * 避免 scale 不同导致的比较失败
     *
     * @param amount 金额
     * @return 如果 amount >= 0 则返回 true
     */
    public static boolean geZero(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        // 使用 compareTo 而不是 equals 来比较 BigDecimal 是否大于等于 0，避免 scale 不同导致的比较失败
        return amount.compareTo(BigDecimal.ZERO) >= 0;
    }

    /**
     * 判断金额是否等于 0
     * 场景说明：
     * 判断金额是否等于 0，注意使用 compareTo 而不是 equals 来比较 BigDecimal 是否等于 0
     * 避免 scale 不同导致的比较失败
     *
     * @param amount 金额
     * @return 如果 amount == 0 则返回 true
     */
    public static boolean eqZero(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        // 使用 compareTo 而不是 equals 来比较 BigDecimal 是否等于 0，避免 scale 不同导致的比较失败
        return amount.compareTo(BigDecimal.ZERO) == 0;
    }

    /**
     * 判断金额是否小于 0
     * 场景说明：
     * 判断金额是否小于 0，注意使用 compareTo 而不是 equals 来比较 BigDecimal 是否小于 0
     * 避免 scale 不同导致的比较失败
     *
     * @param amount 金额
     * @return 如果 amount < 0 则返回 true
     */
    public static boolean ltZero(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        // 使用 compareTo 而不是 equals 来比较 BigDecimal 是否小于 0，避免 scale 不同导致的比较失败
        return amount.compareTo(BigDecimal.ZERO) < 0;
    }

    // =====================================================
    // 数值工具
    // =====================================================

    /**
     * 获取两个金额中的较大值
     * 场景说明：
     * 获取两个金额中的较大值，注意 BigDecimal 的 max 方法会返回两个数中较大的一个
     * 注意它不会修改原有的 BigDecimal 对象，而是返回一个新的对象
     *
     * @param a 第一个数
     * @param b 第二个数
     * @return 较大的数
     */
    public static BigDecimal max(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.max(b);
    }

    /**
     * 获取两个金额中的较小值
     * 场景说明：
     * 获取两个金额中的较小值，注意 BigDecimal 的 min 方法会返回两个数中较小的一个
     * 注意它不会修改原有的 BigDecimal 对象，而是返回一个新的对象
     *
     * @param a 第一个数
     * @param b 第二个数
     * @return 较小的数
     */
    public static BigDecimal min(BigDecimal a, BigDecimal b) {
        checkNotNull(a, b);
        return a.min(b);
    }

    /**
     * 获取金额的绝对值
     * 场景说明：
     * 获取金额的绝对值，注意 BigDecimal 的 abs 方法会返回金额的绝对值
     * 注意它不会修改原有的 BigDecimal 对象，而是返回一个新的对象
     *
     * @param amount 金额
     * @return 绝对值
     */
    public static BigDecimal abs(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        return amount.abs();
    }

    /**
     * 获取金额的相反数
     * 场景说明：
     * 获取金额的相反数，注意 BigDecimal 的 negate 方法会返回金额的相反数
     * 注意它不会修改原有的 BigDecimal 对象，而是返回一个新的对象
     *
     * @param amount 金额
     * @return 相反数
     */
    public static BigDecimal negate(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        return amount.negate();
    }

    /**
     * 将金额限制在一个范围内
     * 场景说明：
     * 将金额限制在一个范围内，如果金额小于最小值，则返回最小值
     * 如果金额大于最大值，则返回最大值；否则返回金额本身
     *
     * @param value 值
     * @param min 最小值
     * @param max 最大值
     * @return 范围内的值
     * @throws IllegalArgumentException 如果 min > max
     */
    public static BigDecimal clamp(BigDecimal value, BigDecimal min, BigDecimal max) {
        Objects.requireNonNull(value, "值不能为空");
        Objects.requireNonNull(min, "最小值不能为空");
        Objects.requireNonNull(max, "最大值不能为空");

        // 先检查 min 和 max 的关系，避免逻辑错误导致的异常情况
        // 如果 min 大于 max，说明参数传递有误，抛出 IllegalArgumentException 异常，提示调用方检查参数
        if (gt(min, max)) {
            throw new IllegalArgumentException("min 不能大于 max");
        }

        // 进行范围限制，如果 value 小于 min，则返回 min；如果 value 大于 max，则返回 max；否则返回 value 本身
        if (lt(value, min)) {
            return min;
        }
        // 进行范围限制，如果 value 大于 max，则返回 max；否则返回 value 本身
        if (gt(value, max)) {
            return max;
        }
        // 如果 value 在 min 和 max 之间，则直接返回 value 本身
        return value;
    }

    /**
     * 范围限制并舍入（法币）
     *
     * @param value 值
     * @param min 最小值
     * @param max 最大值
     * @param currency 货币类型
     * @return 范围内的值，按货币规则舍入
     */
    public static BigDecimal clamp(BigDecimal value, BigDecimal min, BigDecimal max, Currency currency) {
        Objects.requireNonNull(currency, "货币类型不能为空");
        return roundMoney(clamp(value, min, max), currency);
    }

    // =====================================================
    // 舍入
    // =====================================================

    /**
     * 对金额进行舍入（按法币规则）
     * 场景说明：
     * 对金额进行舍入，注意 BigDecimal 的 setScale 方法会返回一个新对象（不会修改原有的 BigDecimal 对象）
     * 例如：对金额进行舍入，或者对��额进行小数位调整等场景，通常需要使用 setScale 方法来实现
     *
     * 说明：
     * return amount.setScale(scale, roundingMode) 表示对金额进行舍入，保留 scale 位小数
     * 并使用 roundingMode 来处理四舍五入
     *
     * @param amount 金额
     * @param currency 货币类型
     * @return 舍入后的金额
     */
    public static BigDecimal roundMoney(BigDecimal amount, Currency currency) {
        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(currency, "货币类型不能为空");
        // 对金额进行舍入，保留 currency.getScale() 位小数
        // 并使用 currency.getRounding() 来处理四舍五入
        return amount.setScale(currency.getScale(), currency.getRounding());
    }

    /**
     * 对 Token 金额进行舍入
     * 场景说明：
     * 对 Token 金额进行舍入，注意 BigDecimal 的 setScale 方法会返回一个新对象（不会修改原有的 BigDecimal 对象）
     * 例如：对 Token 金额进行舍入，或者对 Token 金额进行小数位调整等场景，通常需要使用 setScale 方法来实现
     *
     * 说明：
     * return amount.setScale(token.getDecimals(), token.getRounding()) 表示对 Token 金额进行舍入，保留 token.getDecimals() 位小数
     * 并使用 token.getRounding() 来处理四舍五入
     *
     * @param amount 金额
     * @param token Token 类型
     * @return 舍入后的金额
     */
    public static BigDecimal roundToken(BigDecimal amount, Token token) {
        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(token, "Token 不能为空");
        // 对 Token 金额进行舍入，保留 token.getDecimals() 位小数
        // 并使用 token.getRounding() 来处理四舍五入
        return amount.setScale(token.getDecimals(), token.getRounding());
    }

    /**
     * 对金额进行舍入（自定义）
     * 场景说明：
     * 对金额进行舍入，注意 BigDecimal 的 setScale 方法会返回一个新对象（不会修改原有的 BigDecimal 对象）
     * 例如：对金额进行舍入，或者对金额进行小数位调整等场景，通常需要使用 setScale 方法来实现
     *
     * 说明：
     * return amount.setScale(decimals, roundingMode) 表示对金额进行舍入，保留 decimals 位小数
     * 并使用 roundingMode 来处理四舍五入
     *
     * @param amount 金额
     * @param decimals 保留小数位数
     * @param roundingMode 舍入模式
     * @return 舍入后的金额
     */
    public static BigDecimal roundToken(
            BigDecimal amount,
            int decimals,
            RoundingMode roundingMode) {

        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(roundingMode, "舍入模式不能为空");
        // 对金额进行舍入，保留 decimals 位小数，并使用 roundingMode 来处理四舍五入
        if (decimals < 0) {
            throw new IllegalArgumentException("decimals 不能小于 0");
        }
        // 对金额进行舍入，保留 decimals 位小数，并使用 roundingMode 来处理四舍五入
        return amount.setScale(decimals, roundingMode);
    }

    // =====================================================
    // 格式化
    // =====================================================

    /**
     * 格式化金额为字符串（含货币符号）
     * 场景说明：
     * 格式化金额为字符串，自动添加货币符号，使用对应货币的默认小数位和舍入模式，简化调用
     * 例如：formatMoney(123.456, Currency.USD) 会返回 "$123.46"
     * formatMoney(123.456, Currency.JPY) 会返回 "¥123"
     * formatMoney(123.456, Currency.CNY) 会返回 "¥123.46"
     *
     * @param amount 金额
     * @param currency 货币类型
     * @return 格式化后的字符串
     */
    public static String formatMoney(BigDecimal amount, Currency currency) {
        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(currency, "货币类型不能为空");
        // 对金额进行舍入，保留 currency.getScale() 位小数
        // 并使用 currency.getRounding() 来处理四舍五入
        BigDecimal rounded = roundMoney(amount, currency);
        // 从 ThreadLocal 获取 DecimalFormatHelper 实例，避免重复创建 DecimalFormat 对象，提升性能
        DecimalFormatHelper helper = DECIMAL_FORMAT_CACHE.get();

        try {
            // 配置 DecimalFormat，根据货币的要求设置小数位数、舍入模式和分组使用，确保格式化输出符合预期
            DecimalFormat df = helper.getFormat();
            // 强制设置小数位数，确保与货币规则一致（最小/最大小数位相同）
            df.setMinimumFractionDigits(currency.getScale());
            df.setMaximumFractionDigits(currency.getScale());
            // 设置舍入模式，与货币定义保持统一
            df.setRoundingMode(currency.getRounding());
            // 开启千分位分组，符合财务金额展示习惯
            df.setGroupingUsed(true);
            // 返回格式化后的字符串，包含货币符号和金额，确保输出符合预期的格式
            return currency.getSymbol() + df.format(rounded);
        } finally {
            DECIMAL_FORMAT_CACHE.remove();  // ✅ 关键：移除 ThreadLocal，避免内存泄漏
        }
    }

    /**
     * 格式化金额为字符串（不含货币符号）
     * 场景说明：
     * 格式化金额为字符串，不添加货币符号，使用对应货币的默认小数位和舍入模式，简化调用
     * 例如：formatMoneyPlain(123.456, Currency.USD) 会返回 "123.46"
     * formatMoneyPlain(123.456, Currency.JPY) 会返回 "123"
     * formatMoneyPlain(123.456, Currency.CNY) 会返回 "123.46"
     *
     * @param amount 金额
     * @param currency 货币类型
     * @return 格式化后的字符串
     */
    public static String formatMoneyPlain(BigDecimal amount, Currency currency) {
        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(currency, "货币类型不能为空");

        BigDecimal rounded = roundMoney(amount, currency);
        DecimalFormatHelper helper = DECIMAL_FORMAT_CACHE.get();

        try {
            DecimalFormat df = helper.getFormat();
            df.setMinimumFractionDigits(currency.getScale());
            df.setMaximumFractionDigits(currency.getScale());
            df.setRoundingMode(currency.getRounding());
            df.setGroupingUsed(true);
            return df.format(rounded);
        } finally {
            DECIMAL_FORMAT_CACHE.remove();  // ✅ 关键：移除 ThreadLocal
        }
    }

    /**
     * 格式化 Token 金额为字符串
     * 场景说明：
     * 格式化 Token 金额为字符串，不添加货币符号，使用对应 Token 的默认小数位和舍入模式，简化调用
     * 例如：formatToken(123.456, Token.ETH) 会返回 "123.456000000000000000"
     * formatToken(123.456, Token.BTC) 会返回 "123.45600000"
     * formatToken(123.456, Token.USDT) 会返回 "123.456000"
     * formatToken(123.456, Token.USDC) 会返回 "123.456000"
     * formatToken(123.456, Token.BNB) 会返回 "123.456000000000000000"
     *
     * @param amount 金额
     * @param token Token 类型
     * @return 格式化后的字符串
     */
    public static String formatToken(BigDecimal amount, Token token) {
        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(token, "Token 不能为空");

        BigDecimal rounded = roundToken(amount, token);
        return rounded.toPlainString();
    }

    /**
     * 格式化 Token 金额为字符串（自定义小数位）
     * 场景说明：
     * 格式化 Token 金额为字符串，不添加货币符号，使用指定的小数位和舍入模式，简化调用
     * 例如：formatToken(123.456, 4, RoundingMode.HALF_UP) 会返回 "123.4560"
     * formatToken(123.456, 2, RoundingMode.HALF_UP) 会返回 "123.45"
     *
     * @param amount 金额
     * @param decimals 小数位数
     * @param roundingMode 舍入模式
     * @return 格式化后的字符串
     */
    public static String formatToken(BigDecimal amount, int decimals, RoundingMode roundingMode) {
        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(roundingMode, "舍入模式不能为空");
        if (decimals < 0) {
            throw new IllegalArgumentException("decimals 不能小于 0");
        }

        // 对金额进行舍入，保留 decimals 位小数，并使用 roundingMode 来处理四舍五入
        BigDecimal rounded = amount.setScale(decimals, roundingMode);
        return rounded.toPlainString();
    }

    // =====================================================
    // 百分比
    // =====================================================

    /**
     * 计算百分比
     * 场景说明：
     * 计算百分比，自动处理分母为零的情况，避免调用方需要额外的 null 检查和异常处理
     * 例如：计算分子占分母的百分比，或者计算一个金额占另一个金额的百分比等场景
     *
     * 实现说明：
     * return ratio.multiply(BigDecimal.valueOf(100)).setScale(scale, DEFAULT_ROUND)
     * 表示计算百分比，先计算分子与分母的比值，保留 scale + 2 位小数以避免过早舍入导致的精度问题
     * 然后乘以 100 得到百分比值，最后再舍入到指定的 scale 位小数，使用默认的舍入模式
     * return BigDecimal.ZERO 表示如果分母为零，直接返回 0%，避免抛出异常，简化调用方的错误处理逻辑
     *
     * 例子：
     * percent(123.456, 2, 2) 会返回 "62.50%"
     * percent(123.456, 0, 2) 会返回 "0.00%"，避免分母为零导致的异常
     *
     * @param numerator 分子
     * @param denominator 分母
     * @param scale 结果小数位
     * @return 百分比值
     */
    public static BigDecimal percent(
            BigDecimal numerator,
            BigDecimal denominator,
            int scale) {

        Objects.requireNonNull(numerator, "分子不能为空");
        Objects.requireNonNull(denominator, "分母不能为空");

        if (eqZero(denominator)) {
            return BigDecimal.ZERO;
        }
        // 计算百分比，先计算分子与分母的比值，保留 scale + 2 位小数以避免过早舍入导致的精度问题
        // 然后乘以 100 得到百分比值，最后再舍入到指定的 scale 位小数，使用默认的舍入模式
        BigDecimal ratio = divide(numerator, denominator, scale + 2, DEFAULT_ROUND);
        return ratio.multiply(BigDecimal.valueOf(100)).setScale(scale, DEFAULT_ROUND);
    }

    /**
     * 计算金额乘以百分比
     * 场景说明：
     * 计算金额乘以百分比，自动处理 null 和 scale 的情况，避免调用方需要额外的 null 检查和参数验证
     * 例如：计算金额乘以百分比，或者计算金额乘以一个比例等场景
     *
     * 实现说明：
     * return amount.multiply(percent).divide(BigDecimal.valueOf(100), scale, roundingMode)
     * 表示计算金额乘以百分比，先将百分比转换为小数（除以 100），然后进行乘法计算
     * 最后再舍入到指定的 scale 位小数，使用指定的舍入模式
     *
     * 例子：
     * multiplyPercent(123.456, 10, 2, RoundingMode.HALF_UP) 会返回 "12.35"，表示计算 123.456 的 10%，结果保留 2 位小数，使用四舍五入的舍入模式
     * multiplyPercent(123.456, 0, 2, RoundingMode.HALF_UP) 会返回 "0.00"，表示计算 123.456 的 0%，结果保留 2 位小数，使用四舍五入的舍入模式
     *
     * @param amount 基准金额
     * @param percent 百分比值
     * @param scale 结果小数位
     * @param roundingMode 舍入模式
     * @return 百分比对应的金额
     */
    public static BigDecimal multiplyPercent(
            BigDecimal amount,
            BigDecimal percent,
            int scale,
            RoundingMode roundingMode) {

        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(percent, "百分比不能为空");
        Objects.requireNonNull(roundingMode, "舍入模式不能为空");
        if (scale < 0) {
            throw new IllegalArgumentException("scale 不能小于 0");
        }
        // 计算金额乘以百分比，先将百分比转换为小数（除以 100），然后进行乘法计算
        // 最后再舍入到指定的 scale 位小数，使用指定的舍入模式
        BigDecimal multiplied = amount.multiply(percent);
        // 计算金额乘以百分比，先将百分比转换为小数（除以 100），然后进行乘法计算，最后再舍入到指定的 scale 位小数，使用指定的舍入模式
        return divide(multiplied, BigDecimal.valueOf(100), scale, roundingMode);
    }

    // =====================================================
    // Web3 单位转换
    // =====================================================

    /**
     * 将原始金额转换为实际金额（按 Token 定义）
     * 场景说明：
     * 将原始金额转换为实际金额，自动处理 null 和 Token 的情况，避免调用方需要额外的 null 检查和参数验证
     * 例如：将原始金额转换为实际金额，或者将 Wei 转换为 ETH，或者将 Satoshi 转换为 BTC 等场景
     *
     * 实现说明：
     * return fromRaw(rawAmount, token.getDecimals())
     * 表示将原始金额转换为实际金额，自动根据 Token 的 decimals 进行缩放，得到实际的金额值
     * 保留 token.getDecimals() 位小数，并使用 token.getRounding() 来处理四舍五入
     *
     * 例子：
     * fromRaw(123456789, Token.ETH) 会返回 "123.456789000000000000"，表示将原始金额 123456789 转换为实际金额
     * 保留 18 位小数（ETH 的 decimals），并使用 ETH 的舍入模式进行处理
     *
     * @param rawAmount 原始金额
     * @param token Token 类型
     * @return 实际金额
     */
    public static BigDecimal fromRaw(BigInteger rawAmount, Token token) {
        Objects.requireNonNull(rawAmount, "原始金额不能为空");
        Objects.requireNonNull(token, "Token 不能为空");
        return fromRaw(rawAmount, token.getDecimals());
    }

    /**
     * 将原始金额转换为实际金额（自定义小数位）
     * 场景说明：
     * 将原始金额转换为实际金额，自动处理 null 和 decimals 的情况，避免调用方需要额外的 null 检查和参数验证
     * 例如：将原始金额转换为实际金额，或者将 Wei 转换为 ETH，或者将 Satoshi 转换为 BTC 等场景
     *
     * 实现说明：
     * return new BigDecimal(rawAmount).divide(divisor, decimals, TOKEN_ROUND)
     * 表示将原始金额转换为 BigDecimal，并根据 decimals 进行缩放，得到实际的金额值
     * 保留 decimals 位小数，并使用 TOKEN_ROUND 来处理四舍五入
     *
     * 例子：
     * fromRaw(123456789, 6) 会返回 "123.456789"，表示将原始金额 123456789 转换为实际金额，保留 6 位小数
     *
     * @param rawAmount 原始金额
     * @param decimals 小数位数
     * @return 实际金额
     */
    public static BigDecimal fromRaw(BigInteger rawAmount, int decimals) {
        Objects.requireNonNull(rawAmount, "原始金额不能为空");
        if (decimals < 0) {
            throw new IllegalArgumentException("decimals 不能小于 0");
        }
        // 将原始金额转换为 BigDecimal，并根据 decimals 进行缩放，得到实际的金额值
        BigDecimal divisor = BigDecimal.TEN.pow(decimals);
        // 将原始金额转换为 BigDecimal，并根据 decimals 进行缩放，得到实际的金额值
        // 例如：fromRaw(123456789, 6) 会返回 "123.456789"
        // 表示将原始金额 123456789 转换为实际金额，保留 6 位小数
        return new BigDecimal(rawAmount).divide(divisor, decimals, TOKEN_ROUND);
    }

    /**
     * 将实际金额转换为原始金额（按 Token 定义）
     *
     * @param amount 实际金额
     * @param token Token 类型
     * @return 原始金额
     */
    public static BigInteger toRaw(BigDecimal amount, Token token) {
        Objects.requireNonNull(amount, "金额不能为空");
        Objects.requireNonNull(token, "Token 不能为空");
        return toRaw(amount, token.getDecimals());
    }

    /**
     * 将实际金额转换为原始金额（自定义小数位）
     * 场景说明：
     * 将实际金额转换为原始金额，自动处理 null 和 decimals 的情况，避免调用方需要额外的 null 检查和参数验证
     * 例如：将实际金额转换为原始金额，或者将 ETH 转换为 Wei，或者将 BTC 转换为 Satoshi 等场景
     *
     * 实现说明：
     * return amount.setScale(decimals, TOKEN_ROUND).multiply(BigDecimal.TEN.pow(decimals)).toBigInteger()
     * 表示将金额转换为原始金额，先对金额进行舍入，保留 decimals 位小数，并使用 TOKEN_ROUND 来处理四舍五入
     * 然后再乘以 10 的 decimals 次方，得到原始金额的整数值，最后转换为 BigInteger 类型
     *
     * 例子：
     * toRaw(123.456789, 6) 会返回 "123456789"，表示将金额 123.456789 转换为原始金额
     * 保留 6 位小数，并使用 TOKEN_ROUND 来处理四舍五入，得到原始金额的整数值 123456789
     *
     * @param amount 实际金额
     * @param decimals 小数位数
     * @return 原始金额
     */
    public static BigInteger toRaw(BigDecimal amount, int decimals) {
        Objects.requireNonNull(amount, "金额不能为空");
        if (decimals < 0) {
            throw new IllegalArgumentException("decimals 不能小于 0");
        }
        // 将金额转换为原始金额，先对金额进行舍入，保留 decimals 位小数，并使用 TOKEN_ROUND 来处理四舍五入
        // 然后再乘以 10 的 decimals 次方，得到原始金额的整数值，最后转换为 BigInteger 类型
        // 将金额转换为原始金额，先对金额进行舍入，保留 decimals 位小数，并使用 TOKEN_ROUND 来处理四舍五入
        // 然后再乘以 10 的 decimals 次方，得到原始金额的整数值，最后转换为 BigInteger 类型
        BigDecimal multiplier = BigDecimal.TEN.pow(decimals);
        // 将金额转换为原始金额，先对金额进行舍入，保留 decimals 位小数，并使用 TOKEN_ROUND 来处理四舍五入
        // 然后再乘以 10 的 decimals 次方，得到原始金额的整数值，最后转换为 BigInteger 类型
        // 例如：toRaw(123.456789, 6) 会返回 "123456789"，表示将金额 123.456789 转换为原始金额
        // 保留 6 位小数，并使用 TOKEN_ROUND 来处理四舍五入，得到原始金额的整数值 123456789
        return amount
                .setScale(decimals, TOKEN_ROUND)
                .multiply(multiplier)
                .toBigInteger();
    }

    // =====================================================
    // ETH 快捷方法
    // =====================================================

    /**
     * Wei 转 ETH
     * 场景说明：
     * 将 Wei 转换为 ETH，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：将 Wei 转换为 ETH，或者将 Satoshi 转换为 BTC 等场景
     *
     * 实现说明：
     * return fromRaw(wei, Token.ETH)
     * 表示将 Wei 转换为 ETH，自动根据 ETH 的 decimals 进行缩放，得到实际的 ETH 金额值
     * 保留 18 位小数，并使用 ETH 的舍入模式进行处理
     *
     * @param wei Wei 金额
     * @return ETH 金额
     */
    public static BigDecimal weiToEth(BigInteger wei) {
        Objects.requireNonNull(wei, "Wei 不能为空");
        // 将 Wei 转换为 ETH，自动根据 ETH 的 decimals 进行缩放，得到实际的 ETH 金额值
        // 保留 18 位小数，并使用 ETH 的舍入模式进行处理
        return fromRaw(wei, Token.ETH);
    }

    /**
     * ETH 转 Wei
     * 场景说明：
     * 将 ETH 转换为 Wei，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：将 ETH 转换为 Wei，或者将 BTC 转换为 Satoshi 等场景
     *
     * 实现说明：
     * return toRaw(eth, Token.ETH)
     * 表示将 ETH 转换为 Wei，自动根据 ETH 的 decimals 进行缩放，得到原始的 Wei 金额值
     * 保留 18 位小数，并使用 ETH 的舍入模式进行处理
     *
     * @param eth ETH 金额
     * @return Wei 金额
     */
    public static BigInteger ethToWei(BigDecimal eth) {
        Objects.requireNonNull(eth, "ETH 不能为空");
        // 将 ETH 转换为 Wei，自动根据 ETH 的 decimals 进行缩放，得到原始的 Wei 金额值
        // 保留 18 位小数，并使用 ETH 的舍入模式进行处理
        return toRaw(eth, Token.ETH);
    }

    // =====================================================
    // BTC 快捷方法
    // =====================================================

    /**
     * Satoshi 转 BTC
     * 场景说明：
     * 将 Satoshi 转换为 BTC，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：将 Satoshi 转换为 BTC，或者将 Wei 转换为 ETH 等场景
     *
     * 实现说明：
     * return fromRaw(sat, Token.BTC)
     * 表示将 Satoshi 转换为 BTC，自动根据 BTC 的 decimals 进行缩放，得到实际的 BTC 金额值
     * 保留 8 位小数，并使用 BTC 的舍入模式进行处理
     *
     * @param sat Satoshi 金额
     * @return BTC 金额
     */
    public static BigDecimal satToBtc(BigInteger sat) {
        Objects.requireNonNull(sat, "Satoshi 不能为空");
        // 将 Satoshi 转换为 BTC，自动根据 BTC 的 decimals 进行缩放，得到实际的 BTC 金额值
        // 保留 8 位小数，并使用 BTC 的舍入模式进行处理
        return fromRaw(sat, Token.BTC);
    }

    /**
     * BTC 转 Satoshi
     * 场景说明：
     * 将 BTC 转换为 Satoshi，自动处理 null 的情况，避免调用方需要额外的 null 检查
     * 例如：将 BTC 转换为 Satoshi，或者将 ETH 转换为 Wei 等场景
     *
     * 实现说明：
     * return toRaw(btc, Token.BTC)
     * 表示将 BTC 转换为 Satoshi，自动根据 BTC 的 decimals 进行缩放，得到原始的 Satoshi 金额值
     * 保留 8 位小数，并使用 BTC 的舍入模式进行处理
     *
     * @param btc BTC 金额
     * @return Satoshi 金额
     */
    public static BigInteger btcToSat(BigDecimal btc) {
        Objects.requireNonNull(btc, "BTC 不能为空");
        // 将 BTC 转换为 Satoshi，自动根据 BTC 的 decimals 进行缩放，得到原始的 Satoshi 金额值
        // 保留 8 位小数，并使用 BTC 的舍入模式进行处理
        return toRaw(btc, Token.BTC);
    }

    // =====================================================
    // 私有方法 统一的 null 检查方法，避免重复代码
    // =====================================================

    /**
     * 统一的 null 检查方法
     * 作用：避免重复代码
     * 说明：检查参数 a 和 b 都不能为 null
     *
     * @param a 第一个参数
     * @param b 第二个参数
     * @throws NullPointerException 如果参数为 null
     */
    private static void checkNotNull(BigDecimal a, BigDecimal b) {
        // 检查参数 a 不能为 null
        Objects.requireNonNull(a, "参数 a 不能为空");
        // 检查参数 b 不能为 null
        Objects.requireNonNull(b, "参数 b 不能为空");
    }

    /**
     * 全脱敏
     * 场景说明：
     * 将金额进行全脱敏，隐藏真实金额信息
     *
     * 实现说明：
     * 如果金额为 0，返回 "***"，否则返回 "******"，实现全脱敏的效果
     *
     * @param amount 金额
     * @return 脱敏后的字符串
     */
    public static String desensitizeAll(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        // 如果金额为 0，返回 "***"，否则返回 "******"，实现全脱敏的效果
        if (eqZero(amount)) {
            return "***";
        }
        return "******";
    }

    // =====================================================
    // 金融验证
    // =====================================================

    /**
     * 判断金额是否为正数（大于 0）
     * 场景说明：
     * 判断金额是否为正数，用于验证金额输入是否合法
     * 例如：检查商品价格、转账金额等必须为正数的场景
     * 
     * @param amount 金额
     * @return 如果 amount > 0 则返回 true，否则返回 false
     */
    public static boolean isPositive(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        return gtZero(amount);
    }

    /**
     * 判断金额是否为负数（小于 0）
     * 场景说明：
     * 判断金额是否为负数，用于验证金额输入是否合法
     * 例如：检查是否为退款、负调整等负数金额场景
     * 
     * @param amount 金额
     * @return 如果 amount < 0 则返回 true，否则返回 false
     */
    public static boolean isNegative(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        return ltZero(amount);
    }

    /**
     * 判断金额是否为零
     * 场景说明：
     * 判断金额是否为零，用于验证金额输入是否合法
     * 例如：检查金额是否为 0，区分 null 和 0 的情况
     * 
     * @param amount 金额
     * @return 如果 amount == 0 则返回 true，否则返回 false
     */
    public static boolean isZero(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        return eqZero(amount);
    }

    /**
     * 判断金额是否为非正数（小于等于 0）
     * 场景说明：
     * 判断金额是否为非正数，用于验证金额输入是否合法
     * 例如：检查金额是否不符合业务要求（必须 > 0）
     * 
     * @param amount 金额
     * @return 如果 amount <= 0 则返回 true，否则返回 false
     */
    public static boolean isNonPositive(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        return le(amount, BigDecimal.ZERO);
    }

    /**
     * 判断金额是否为非负数（大于等于 0）
     * 场景说明：
     * 判断金额是否为非负数，用于验证金额输入是否合法
     * 例如：检查金额是否符合业务要求（>= 0）
     * 
     * @param amount 金额
     * @return 如果 amount >= 0 则返回 true，否则返回 false
     */
    public static boolean isNonNegative(BigDecimal amount) {
        Objects.requireNonNull(amount, "金额不能为空");
        return ge(amount, BigDecimal.ZERO);
    }

    /**
     * 判断金额是否有效（符合法币规则）
     * 场景说明：
     * 判断金额是否有效，包括检查小数位数是否符合货币规则
     * 例如：检查 USD 金额是否只有 2 位小数、JPY 是否有小数部分等
     * 
     * 验证规则：
     * 1. 金额不能为 null
     * 2. 金额必须为正数或零
     * 3. 金额的小数位数不能超过货币规定的小数位数
     * 
     * @param amount 金额
     * @param currency 货币类型
     * @return 如果金额有效则返回 true，否则返回 false
     */
    public static boolean isValidCurrency(BigDecimal amount, Currency currency) {
        if (amount == null) {
            return false;
        }
        if (currency == null) {
            return false;
        }
        
        // 检查金额是否为非负数
        if (isNegative(amount)) {
            return false;
        }
        
        // 检查金额的小数位数是否符合货币规则
        // 获取金额的 scale（小数位数）
        int amountScale = amount.scale();
        int currencyScale = currency.getScale();
        
        // 小数位数不能超过货币规定的小数位数
        // 例如：USD 规定 2 位小数，金额不能有 3 位或以上小数
        if (amountScale > currencyScale) {
            return false;
        }
        
        return true;
    }

    /**
     * 判断金额是否有效（符合 Token 规则）
     * 场景说明：
     * 判断金额是否有效，包括检查小数位数是否符合 Token 规则
     * 例如：检查 ETH 金额是否只有 18 位小数、BTC 是否只有 8 位小数等
     * 
     * 验证规则：
     * 1. 金额不能为 null
     * 2. 金额必须为正数或零
     * 3. 金额的小数位数不能超过 Token 规定的小数位数
     * 
     * @param amount 金额
     * @param token Token 类型
     * @return 如果金额有效则返回 true，否则返回 false
     */
    public static boolean isValidToken(BigDecimal amount, Token token) {
        if (amount == null) {
            return false;
        }
        if (token == null) {
            return false;
        }
        
        // 检查金额是否为非负数
        if (isNegative(amount)) {
            return false;
        }
        
        // 检查金额的小数位数是否符合 Token 规则
        // 获取金额的 scale（小数位数）
        int amountScale = amount.scale();
        int tokenDecimals = token.getDecimals();
        
        // 小数位数不能超过 Token 规定的小数位数
        // 例如：ETH 规定 18 位小数，金额不能有 19 位或以上小数
        if (amountScale > tokenDecimals) {
            return false;
        }
        
        return true;
    }

    /**
     * 判断金额范围是否有效
     * 场景说明：
     * 判断金额是否在指定的范围内，用于检查金额是否符合业务约束
     * 例如：检查订单金额是否在 [0.01, 999999.99] 范围内
     * 
     * 验证规则：
     * 1. 金额不能为 null
     * 2. 金额必须 >= minAmount
     * 3. 金额必须 <= maxAmount
     * 4. minAmount <= maxAmount
     * 
     * @param amount 金额
     * @param minAmount 最小金额（包含）
     * @param maxAmount 最大金额（包含）
     * @return 如果金额在范围内则返回 true，否则返回 false
     */
    public static boolean isInRange(BigDecimal amount, BigDecimal minAmount, BigDecimal maxAmount) {
        if (amount == null || minAmount == null || maxAmount == null) {
            return false;
        }
        
        // 检查参数顺序是否正确
        if (gt(minAmount, maxAmount)) {
            return false;
        }
        
        // 检查金额是否在范围内
        return ge(amount, minAmount) && le(amount, maxAmount);
    }

    /**
     * 判断金额范围是否有效（法币版本）
     * 场景说明：
     * 判断金额是否在指定的范围内并符合法币规则
     * 例如：检查 USD 订单金额是否在 [0.01, 999999.99] 范围内且只有 2 位小数
     * 
     * 验证规则：
     * 1. 金额必须有效（符合法币规则）
     * 2. 金额必须在指定范围内
     * 
     * @param amount 金额
     * @param minAmount 最小金额（包含）
     * @param maxAmount 最大金额（包含）
     * @param currency 货币类型
     * @return 如果金额有效且在范围内则返回 true，否则返回 false
     */
    public static boolean isValidCurrencyRange(
            BigDecimal amount,
            BigDecimal minAmount,
            BigDecimal maxAmount,
            Currency currency) {
        
        // 先检查金额是否符合货币规则
        if (!isValidCurrency(amount, currency)) {
            return false;
        }
        
        // 再检查金额是否在范围内
        return isInRange(amount, minAmount, maxAmount);
    }

    /**
     * 判断金额范围是否有效（Token 版本）
     * 场景说明：
     * 判断金额是否在指定的范围内并符合 Token 规则
     * 例如：检查 ETH 转账金额是否在 [0.001, 1000] 范围内且只有 18 位小数
     * 
     * 验证规则：
     * 1. 金额必须有效（符合 Token 规则）
     * 2. 金额必须在指定范围内
     * 
     * @param amount 金额
     * @param minAmount 最小金额（包含）
     * @param maxAmount 最大金额（包含）
     * @param token Token 类型
     * @return 如果金额有效且在范围内则返回 true，否则返回 false
     */
    public static boolean isValidTokenRange(
            BigDecimal amount,
            BigDecimal minAmount,
            BigDecimal maxAmount,
            Token token) {
        
        // 先检查金额是否符合 Token 规则
        if (!isValidToken(amount, token)) {
            return false;
        }
        
        // 再检查金额是否在范围内
        return isInRange(amount, minAmount, maxAmount);
    }

}
