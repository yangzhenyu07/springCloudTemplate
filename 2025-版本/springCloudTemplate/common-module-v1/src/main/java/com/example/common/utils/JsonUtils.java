package com.example.common.utils;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONReader;
import com.alibaba.fastjson2.JSONWriter;
import com.alibaba.fastjson2.TypeReference;

import java.util.List;

/**
 * JSON 工具类（基于 Fastjson2）
 *
 * @author yzy
 */
public final class JsonUtils {

    private JsonUtils() {
    }

    /**
     * 对象转 JSON 字符串
     */
    public static String toJson(Object obj) {
        if (obj == null) {
            return null;
        }
        return JSON.toJSONString(obj, JSONWriter.Feature.WriteMapNullValue);
    }

    /**
     * 对象转 JSON 字符串（不输出 null 字段）
     */
    public static String toJsonNonNull(Object obj) {
        if (obj == null) {
            return null;
        }
        return JSON.toJSONString(obj);
    }

    /**
     * JSON 字符串转对象
     */
    public static <T> T fromJson(String json, Class<T> clazz) {
        if (json == null || json.isEmpty()) {
            return null;
        }
        return JSON.parseObject(json, clazz);
    }

    /**
     * JSON 字符串转对象（支持泛型集合等复杂类型）
     */
    public static <T> T fromJson(String json, TypeReference<T> typeReference) {
        if (json == null || json.isEmpty()) {
            return null;
        }
        return JSON.parseObject(json, typeReference);
    }

    /**
     * JSON 字符串转 List
     */
    public static <T> List<T> fromJsonList(String json, Class<T> clazz) {
        if (json == null || json.isEmpty()) {
            return null;
        }
        return JSON.parseArray(json, clazz);
    }

    /**
     * 对象转 byte[]
     */
    public static byte[] toBytes(Object obj) {
        if (obj == null) {
            return new byte[0];
        }
        return JSON.toJSONBytes(obj);
    }

    /**
     * byte[] 转对象
     */
    public static <T> T fromBytes(byte[] bytes, Class<T> clazz) {
        if (bytes == null || bytes.length == 0) {
            return null;
        }
        return JSON.parseObject(bytes, clazz, JSONReader.Feature.SupportAutoType);
    }
}
