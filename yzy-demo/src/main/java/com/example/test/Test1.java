package com.example.test;

import java.math.BigDecimal;
import java.text.DecimalFormat;

public class Test1 {

    /**
     * 提供精确的减法运算
     *
     * @param v1
     * @param v2
     * @return
     */
    public static double subtract(double v1, double v2) {
        BigDecimal b1 = new BigDecimal(v1);
        BigDecimal b2 = new BigDecimal(v2);
        return b1.subtract(b2).doubleValue();
    }
    /**
     * 提供精确的乘法运算
     *
     * @param v1
     * @param v2
     * @return
     */
    public static double multiply(double v1, double v2) {
        BigDecimal b1 = new BigDecimal(v1);
        BigDecimal b2 = new BigDecimal(v2);
        return b1.multiply(b2).doubleValue();
    }
    /**
     * 提供精确的加法运算
     *
     * @param v1
     * @param v2
     * @return
     */
    public static double add(double v1, double v2) {
        BigDecimal b1 = new BigDecimal(v1);
        BigDecimal b2 = new BigDecimal(v2);
        return b1.add(b2).doubleValue();
    }
    /**
     * 保留小数点后两位
     */
    public static void main(String[] args) {
        //保留两位小数
        System.out.println("保留两位小数："+new BigDecimal(0.2351).setScale(2, BigDecimal.ROUND_HALF_UP).doubleValue());

        //保留两位小数
        BigDecimal lastValue = new BigDecimal("12");
        BigDecimal pp =  lastValue.add(new BigDecimal("56.567"));
        DecimalFormat df = new DecimalFormat("#0.00");
//        System.out.println("保留两位小数，对应位上无数字填充0："+df.format(pp.doubleValue()));// 0.20
//        BigDecimal a = BigDecimal.ZERO;
//        BigDecimal b =BigDecimal.TEN;
//        BigDecimal bigDecimal = new BigDecimal(0.1);
    }



}
