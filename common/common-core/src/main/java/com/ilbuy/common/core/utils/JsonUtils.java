package com.ilbuy.common.core.utils;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import lombok.extern.slf4j.Slf4j;

import java.util.List;
import java.util.Map;

/**
 * JSON 工具类（基于 Jackson，全局单例 ObjectMapper）
 */
@Slf4j
public final class JsonUtils {

    private JsonUtils() {}

    private static final ObjectMapper MAPPER = buildMapper();

    private static ObjectMapper buildMapper() {
        ObjectMapper om = new ObjectMapper();
        // Java 8 Time 模块
        om.registerModule(new JavaTimeModule());
        // 不将日期序列化为时间戳
        om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        // 反序列化时忽略未知字段
        om.disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
        // null 字段不输出（可根据需要关闭）
        om.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        return om;
    }

    /**
     * 获取全局 ObjectMapper 实例（如需自定义配置）
     */
    public static ObjectMapper getMapper() {
        return MAPPER;
    }

    /**
     * 对象转 JSON 字符串
     */
    public static String toJson(Object obj) {
        if (obj == null) return null;
        try {
            return MAPPER.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("[JsonUtils] toJson error, obj={}", obj.getClass().getName(), e);
            throw new IllegalArgumentException("JSON 序列化失败: " + e.getMessage(), e);
        }
    }

    /**
     * JSON 字符串转对象
     */
    public static <T> T fromJson(String json, Class<T> clazz) {
        if (json == null || json.isBlank()) return null;
        try {
            return MAPPER.readValue(json, clazz);
        } catch (JsonProcessingException e) {
            log.error("[JsonUtils] fromJson error, type={}", clazz.getName(), e);
            throw new IllegalArgumentException("JSON 反序列化失败: " + e.getMessage(), e);
        }
    }

    /**
     * JSON 字符串转复杂泛型（如 List&lt;User&gt;）
     * <pre>{@code
     * List<User> users = JsonUtils.fromJson(json, new TypeReference<List<User>>(){});
     * }</pre>
     */
    public static <T> T fromJson(String json, TypeReference<T> typeRef) {
        if (json == null || json.isBlank()) return null;
        try {
            return MAPPER.readValue(json, typeRef);
        } catch (JsonProcessingException e) {
            log.error("[JsonUtils] fromJson typeRef error", e);
            throw new IllegalArgumentException("JSON 反序列化失败: " + e.getMessage(), e);
        }
    }

    /**
     * JSON 字符串转 List
     */
    public static <T> List<T> fromJsonList(String json, Class<T> elementClass) {
        if (json == null || json.isBlank()) return List.of();
        try {
            return MAPPER.readValue(json,
                    MAPPER.getTypeFactory().constructCollectionType(List.class, elementClass));
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("JSON 反序列化失败: " + e.getMessage(), e);
        }
    }

    /**
     * JSON 字符串转 Map&lt;String, Object&gt;
     */
    @SuppressWarnings("unchecked")
    public static Map<String, Object> fromJsonMap(String json) {
        return fromJson(json, Map.class);
    }

    /**
     * 对象转换（利用 Jackson 做深度对象映射）
     */
    public static <T> T convert(Object obj, Class<T> targetClass) {
        return MAPPER.convertValue(obj, targetClass);
    }

    /**
     * 格式化（美化）JSON 字符串
     */
    public static String prettyPrint(Object obj) {
        try {
            return MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            return obj.toString();
        }
    }
}
