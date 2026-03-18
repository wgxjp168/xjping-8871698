package com.ilbuy.common.core.enums;

/**
 * 业务枚举基接口
 *
 * <p>所有业务枚举实现此接口，统一提供 code/description，
 * 并支持通过 code 反查枚举值（配合 MyBatis-Plus TypeHandler 使用）。</p>
 *
 * <pre>{@code
 * public enum OrderStatus implements BaseEnum<Integer> {
 *     PENDING(0, "待支付"),
 *     PAID(1, "已支付"),
 *     SHIPPED(2, "已发货"),
 *     COMPLETED(3, "已完成"),
 *     CANCELLED(4, "已取消");
 *
 *     private final int code;
 *     private final String description;
 *
 *     OrderStatus(int code, String description) {
 *         this.code        = code;
 *         this.description = description;
 *     }
 *
 *     @Override public Integer getCode() { return code; }
 *     @Override public String getDescription() { return description; }
 * }
 *
 * // 反查
 * OrderStatus status = BaseEnum.of(OrderStatus.class, 1); // → PAID
 * }</pre>
 *
 * @param <T> code 类型（通常为 Integer 或 String）
 */
public interface BaseEnum<T> {

    /**
     * 枚举码值（数据库存储值）
     */
    T getCode();

    /**
     * 枚举描述（界面展示文本）
     */
    String getDescription();

    /**
     * 根据 code 查找枚举值
     *
     * @param enumClass 枚举 Class
     * @param code      码值
     * @param <E>       枚举类型
     * @param <T>       code 类型
     * @return 对应枚举，不存在则返回 null
     */
    static <E extends Enum<E> & BaseEnum<T>, T> E of(Class<E> enumClass, T code) {
        if (code == null) return null;
        for (E constant : enumClass.getEnumConstants()) {
            if (code.equals(constant.getCode())) {
                return constant;
            }
        }
        return null;
    }

    /**
     * 根据 code 查找枚举值，找不到抛出 IllegalArgumentException
     */
    static <E extends Enum<E> & BaseEnum<T>, T> E ofRequired(Class<E> enumClass, T code) {
        E result = of(enumClass, code);
        if (result == null) {
            throw new IllegalArgumentException(
                    "枚举 " + enumClass.getSimpleName() + " 中不存在 code=" + code);
        }
        return result;
    }

    /**
     * 判断 code 是否存在于枚举中
     */
    static <E extends Enum<E> & BaseEnum<T>, T> boolean contains(Class<E> enumClass, T code) {
        return of(enumClass, code) != null;
    }
}
