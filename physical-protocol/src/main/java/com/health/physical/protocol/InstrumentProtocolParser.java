package com.health.physical.protocol;

/**
 * 仪器协议解析器顶层接口
 *
 * @param <T> 解析结果类型
 */
public interface InstrumentProtocolParser<T> {

    /**
     * 解析仪器报文
     *
     * @param rawMessage 原始报文字节/字符串（由子接口决定形式）
     * @return 解析结果
     */
    T parse(String rawMessage);

    /**
     * 判断该解析器是否支持该报文（根据设备型号/报文特征判断）
     */
    boolean supports(String rawMessage);
}
