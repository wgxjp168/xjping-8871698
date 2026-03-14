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
 * JSON序列化/反序列化工具类
 *
 * <p>基于Jackson，统一JSON配置：
 * <ul>
 *   <li>忽略未知字段（容错）</li>
 *   <li>Java 8日期时间支持</li>
 *   <li>空值字段不序列化</li>
 * </ul>
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
public final class JsonUtils {

    private static final ObjectMapper MAPPER;

    static {
        MAPPER = new ObjectMapper();
        // 忽略JSON中未知字段
        MAPPER.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        // 枚举使用toString而非name
        MAPPER.configure(SerializationFeature.WRITE_ENUMS_USING_TO_STRING, false);
        // 禁止日期序列化为时间戳
        MAPPER.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);
        // Java 8 时间类型支持
        MAPPER.registerModule(new JavaTimeModule());
        // 空值不序列化
        MAPPER.setSerializationInclusion(JsonInclude.Include.NON_NULL);
    }

    private JsonUtils() {}

    /**
     * 对象序列化为JSON字符串
     *
     * @param obj 对象
     * @return JSON字符串，失败返回null
     */
    public static String toJson(Object obj) {
        if (obj == null) {
            return null;
        }
        try {
            return MAPPER.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("[JsonUtils] 序列化失败: {}", obj.getClass().getName(), e);
            return null;
        }
    }

    /**
     * JSON字符串反序列化为对象
     *
     * @param json  JSON字符串
     * @param clazz 目标类型
     * @return 对象，失败返回null
     */
    public static <T> T fromJson(String json, Class<T> clazz) {
        if (json == null || json.isEmpty()) {
            return null;
        }
        try {
            return MAPPER.readValue(json, clazz);
        } catch (JsonProcessingException e) {
            log.error("[JsonUtils] 反序列化失败: {}", clazz.getName(), e);
            return null;
        }
    }

    /**
     * JSON字符串反序列化为泛型对象（用于List、Map等）
     *
     * <p>示例：
     * <pre>{@code
     * List<UserDTO> list = JsonUtils.fromJson(json, new TypeReference<List<UserDTO>>() {});
     * }</pre>
     *
     * @param json          JSON字符串
     * @param typeReference 类型引用
     */
    public static <T> T fromJson(String json, TypeReference<T> typeReference) {
        if (json == null || json.isEmpty()) {
            return null;
        }
        try {
            return MAPPER.readValue(json, typeReference);
        } catch (JsonProcessingException e) {
            log.error("[JsonUtils] 反序列化失败: {}", typeReference.getType(), e);
            return null;
        }
    }

    /**
     * JSON字符串反序列化为List
     *
     * @param json      JSON字符串
     * @param itemClass 列表元素类型
     */
    public static <T> List<T> fromJsonList(String json, Class<T> itemClass) {
        if (json == null || json.isEmpty()) {
            return List.of();
        }
        try {
            return MAPPER.readValue(json,
                    MAPPER.getTypeFactory().constructCollectionType(List.class, itemClass));
        } catch (JsonProcessingException e) {
            log.error("[JsonUtils] 反序列化List失败: {}", itemClass.getName(), e);
            return List.of();
        }
    }

    /**
     * 对象转Map
     *
     * @param obj 对象
     */
    @SuppressWarnings("unchecked")
    public static Map<String, Object> toMap(Object obj) {
        return MAPPER.convertValue(obj, Map.class);
    }

    /**
     * 深拷贝对象（通过JSON序列化/反序列化实现）
     *
     * @param obj   源对象
     * @param clazz 目标类型
     */
    public static <T> T deepCopy(Object obj, Class<T> clazz) {
        return fromJson(toJson(obj), clazz);
    }

    /**
     * 获取Jackson ObjectMapper实例（扩展使用）
     */
    public static ObjectMapper getMapper() {
        return MAPPER;
    }
}
