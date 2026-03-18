package com.ilbuy.common.core.utils;

import cn.hutool.crypto.SecureUtil;
import cn.hutool.crypto.asymmetric.KeyType;
import cn.hutool.crypto.asymmetric.RSA;
import cn.hutool.crypto.symmetric.AES;
import lombok.extern.slf4j.Slf4j;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.util.Base64;

/**
 * 加密工具类
 * <p>支持：MD5、SHA256、AES-128（CBC/PKCS5）、RSA-2048</p>
 *
 * <pre>{@code
 * // MD5
 * String hash = EncryptUtils.md5("hello");
 * // AES 加解密
 * String key  = EncryptUtils.genAesKey();
 * String enc  = EncryptUtils.aesEncrypt("plaintext", key);
 * String dec  = EncryptUtils.aesDecrypt(enc, key);
 * // RSA
 * KeyPair kp       = EncryptUtils.genRsaKeyPair();
 * String  pubKey   = EncryptUtils.base64(kp.getPublic().getEncoded());
 * String  priKey   = EncryptUtils.base64(kp.getPrivate().getEncoded());
 * String  cipher   = EncryptUtils.rsaEncrypt("data", pubKey);
 * String  plain    = EncryptUtils.rsaDecrypt(cipher, priKey);
 * }</pre>
 */
@Slf4j
public final class EncryptUtils {

    private EncryptUtils() {}

    // ──────────────────── MD5 ────────────────────

    /**
     * MD5 摘要（32位小写十六进制）
     */
    public static String md5(String input) {
        return SecureUtil.md5(input);
    }

    /**
     * MD5 加盐摘要
     */
    public static String md5WithSalt(String input, String salt) {
        return SecureUtil.md5(input + salt);
    }

    // ──────────────────── SHA ────────────────────

    public static String sha256(String input) {
        return SecureUtil.sha256(input);
    }

    public static String sha512(String input) {
        return cn.hutool.crypto.digest.DigestUtil.sha512Hex(input);
    }

    // ──────────────────── AES ────────────────────

    /**
     * 生成 AES-128 密钥（Base64 编码）
     */
    public static String genAesKey() {
        return Base64.getEncoder().encodeToString(SecureUtil.generateKey("AES", 128).getEncoded());
    }

    /**
     * AES 加密（CBC + PKCS5Padding）
     *
     * @param plainText 明文
     * @param base64Key Base64 编码的 AES 密钥
     * @return Base64 编码的密文
     */
    public static String aesEncrypt(String plainText, String base64Key) {
        AES aes = buildAes(base64Key);
        return aes.encryptBase64(plainText, StandardCharsets.UTF_8);
    }

    /**
     * AES 解密
     *
     * @param cipherText Base64 编码的密文
     * @param base64Key  Base64 编码的 AES 密钥
     * @return 明文
     */
    public static String aesDecrypt(String cipherText, String base64Key) {
        AES aes = buildAes(base64Key);
        return aes.decryptStr(cipherText, StandardCharsets.UTF_8);
    }

    private static AES buildAes(String base64Key) {
        byte[] keyBytes = Base64.getDecoder().decode(base64Key);
        return SecureUtil.aes(keyBytes);
    }

    // ──────────────────── RSA ────────────────────

    /**
     * 生成 RSA-2048 密钥对
     */
    public static KeyPair genRsaKeyPair() {
        return SecureUtil.generateKeyPair("RSA", 2048);
    }

    /**
     * RSA 公钥加密
     *
     * @param plainText    明文
     * @param base64PubKey Base64 编码的公钥
     * @return Base64 编码的密文
     */
    public static String rsaEncrypt(String plainText, String base64PubKey) {
        RSA rsa = new RSA(null, base64PubKey);
        return rsa.encryptBase64(plainText, StandardCharsets.UTF_8, KeyType.PublicKey);
    }

    /**
     * RSA 私钥解密
     *
     * @param cipherText    Base64 编码的密文
     * @param base64PriKey  Base64 编码的私钥
     * @return 明文
     */
    public static String rsaDecrypt(String cipherText, String base64PriKey) {
        RSA rsa = new RSA(base64PriKey, null);
        return rsa.decryptStr(cipherText, KeyType.PrivateKey, StandardCharsets.UTF_8);
    }

    // ──────────────────── Base64 ────────────────────

    public static String base64(byte[] bytes) {
        return Base64.getEncoder().encodeToString(bytes);
    }

    public static byte[] base64Decode(String base64) {
        return Base64.getDecoder().decode(base64);
    }

    public static String base64UrlEncode(byte[] bytes) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}
