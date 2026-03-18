package com.ilbuy.common.core.utils;

import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;

import java.net.InetAddress;
import java.net.UnknownHostException;

/**
 * IP 工具类（支持代理透传真实 IP）
 */
@Slf4j
public final class IpUtils {

    private IpUtils() {}

    private static final String UNKNOWN  = "unknown";
    private static final String LOOPBACK = "127.0.0.1";

    /**
     * 获取请求真实 IP（支持多级代理）
     */
    public static String getRealIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (isInvalidIp(ip)) ip = request.getHeader("Proxy-Client-IP");
        if (isInvalidIp(ip)) ip = request.getHeader("WL-Proxy-Client-IP");
        if (isInvalidIp(ip)) ip = request.getHeader("HTTP_CLIENT_IP");
        if (isInvalidIp(ip)) ip = request.getHeader("HTTP_X_FORWARDED_FOR");
        if (isInvalidIp(ip)) ip = request.getHeader("X-Real-IP");
        if (isInvalidIp(ip)) ip = request.getRemoteAddr();

        // X-Forwarded-For 多 IP 取第一个
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }

        // 本机 IPv6 转 IPv4
        if ("0:0:0:0:0:0:0:1".equals(ip) || "::1".equals(ip)) {
            ip = LOOPBACK;
        }

        return ip;
    }

    /**
     * 判断是否内网 IP
     */
    public static boolean isInternalIp(String ip) {
        try {
            InetAddress addr = InetAddress.getByName(ip);
            return addr.isSiteLocalAddress()
                    || addr.isLoopbackAddress()
                    || addr.isLinkLocalAddress();
        } catch (UnknownHostException e) {
            return false;
        }
    }

    private static boolean isInvalidIp(String ip) {
        return ip == null || ip.isBlank() || UNKNOWN.equalsIgnoreCase(ip);
    }
}
