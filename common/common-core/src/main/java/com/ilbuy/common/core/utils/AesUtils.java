package com.ilbuy.common.core.utils;

import lombok.extern.slf4j.Slf4j;
import org.bouncycastle.jce.provider.BouncyCastleProvider;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.security.SecureRandom;
import java.security.Security;
import java.util.Base64;

/**
 * AES-256-GCM 加解密工具类
 *
 * <p>采用 AES-256-GCM 模式，特点：
 * <ul>
 *   <li>提供认证加密（AEAD），防篡改</li>
 *   <li>每次加密随机生成12字节IV，避免重放攻击</li>
 *   <li>密文格式：IV(12B) + 密文 + 认证Tag(16B)，Base64编码</li>
 * </ul>
 *
 * <p>使用场景：用户手机号/邮箱/支付信息等敏感字段加密存储
 *
 * @author ILbuy Team
 * @version 1.0.0
 */
@Slf4j
public final class AesUtils {

    static {
        Security.addProvider(new BouncyCastleProvider());
    }

    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int KEY_SIZE = 256;          // 密钥长度（位）
    private static final int IV_LENGTH = 12;          // GCM推荐IV长度（字节）
    private static final int TAG_LENGTH_BIT = 128;    // 认证Tag长度（位）

    private AesUtils() {}

    /**
     * 生成256位AES密钥（Base64编码）
     *
     * @return Base64编码的密钥字符串
     */
    public static String generateKey() {
        try {
            KeyGenerator keyGen = KeyGenerator.getInstance("AES");
            keyGen.init(KEY_SIZE, new SecureRandom());
            SecretKey secretKey = keyGen.generateKey();
            return Base64.getEncoder().encodeToString(secretKey.getEncoded());
        } catch (Exception e) {
            throw new RuntimeException("生成AES密钥失败", e);
        }
    }

    /**
     * AES-256-GCM 加密
     *
     * @param plainText  明文
     * @param base64Key  Base64编码的256位密钥
     * @return Base64编码的密文（包含IV）
     */
    public static String encrypt(String plainText, String base64Key) {
        if (plainText == null || plainText.isEmpty()) {
            return plainText;
        }
        try {
            byte[] keyBytes = Base64.getDecoder().decode(base64Key);
            SecretKeySpec keySpec = new SecretKeySpec(keyBytes, "AES");

            // 随机生成12字节IV
            byte[] iv = new byte[IV_LENGTH];
            new SecureRandom().nextBytes(iv);

            Cipher cipher = Cipher.getInstance(ALGORITHM, "BC");
            GCMParameterSpec paramSpec = new GCMParameterSpec(TAG_LENGTH_BIT, iv);
            cipher.init(Cipher.ENCRYPT_MODE, keySpec, paramSpec);

            byte[] cipherText = cipher.doFinal(plainText.getBytes("UTF-8"));

            // 拼接 IV + 密文
            ByteBuffer byteBuffer = ByteBuffer.allocate(iv.length + cipherText.length);
            byteBuffer.put(iv);
            byteBuffer.put(cipherText);

            return Base64.getEncoder().encodeToString(byteBuffer.array());
        } catch (Exception e) {
            log.error("[AesUtils] 加密失败", e);
            throw new RuntimeException("数据加密失败", e);
        }
    }

    /**
     * AES-256-GCM 解密
     *
     * @param encryptedText  Base64编码的密文（包含IV）
     * @param base64Key      Base64编码的256位密钥
     * @return 明文
     */
    public static String decrypt(String encryptedText, String base64Key) {
        if (encryptedText == null || encryptedText.isEmpty()) {
            return encryptedText;
        }
        try {
            byte[] keyBytes = Base64.getDecoder().decode(base64Key);
            SecretKeySpec keySpec = new SecretKeySpec(keyBytes, "AES");

            byte[] decoded = Base64.getDecoder().decode(encryptedText);

            // 提取IV（前12字节）
            ByteBuffer byteBuffer = ByteBuffer.wrap(decoded);
            byte[] iv = new byte[IV_LENGTH];
            byteBuffer.get(iv);

            // 提取密文
            byte[] cipherText = new byte[byteBuffer.remaining()];
            byteBuffer.get(cipherText);

            Cipher cipher = Cipher.getInstance(ALGORITHM, "BC");
            GCMParameterSpec paramSpec = new GCMParameterSpec(TAG_LENGTH_BIT, iv);
            cipher.init(Cipher.DECRYPT_MODE, keySpec, paramSpec);

            byte[] plainText = cipher.doFinal(cipherText);
            return new String(plainText, "UTF-8");
        } catch (Exception e) {
            log.error("[AesUtils] 解密失败", e);
            throw new RuntimeException("数据解密失败", e);
        }
    }
}
