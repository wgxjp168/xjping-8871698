package com.ilbuy.common.core.utils;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * AES加解密工具单元测试
 *
 * @author ILbuy Team
 */
@DisplayName("AES加解密工具测试")
class AesUtilsTest {

    private String key;

    @BeforeEach
    void setUp() {
        key = AesUtils.generateKey();
    }

    @Test
    @DisplayName("生成密钥不为空")
    void testGenerateKey() {
        assertThat(key).isNotBlank();
        // Base64解码后应为32字节（256位）
        byte[] keyBytes = java.util.Base64.getDecoder().decode(key);
        assertThat(keyBytes).hasSize(32);
    }

    @Test
    @DisplayName("加解密手机号")
    void testEncryptDecryptPhone() {
        String phone = "13812345678";
        String encrypted = AesUtils.encrypt(phone, key);
        assertThat(encrypted).isNotEqualTo(phone);

        String decrypted = AesUtils.decrypt(encrypted, key);
        assertThat(decrypted).isEqualTo(phone);
    }

    @Test
    @DisplayName("加解密中文内容")
    void testEncryptDecryptChinese() {
        String text = "我来购AI采购决策平台测试文本";
        String encrypted = AesUtils.encrypt(text, key);
        String decrypted = AesUtils.decrypt(encrypted, key);
        assertThat(decrypted).isEqualTo(text);
    }

    @Test
    @DisplayName("相同明文多次加密结果不同（IV随机）")
    void testEncryptProduceDifferentCiphertext() {
        String text = "sensitive_data";
        String enc1 = AesUtils.encrypt(text, key);
        String enc2 = AesUtils.encrypt(text, key);
        // 每次加密IV随机，密文不同
        assertThat(enc1).isNotEqualTo(enc2);
        // 但解密结果相同
        assertThat(AesUtils.decrypt(enc1, key)).isEqualTo(text);
        assertThat(AesUtils.decrypt(enc2, key)).isEqualTo(text);
    }

    @Test
    @DisplayName("空值处理")
    void testNullAndEmpty() {
        assertThat(AesUtils.encrypt(null, key)).isNull();
        assertThat(AesUtils.encrypt("", key)).isEmpty();
        assertThat(AesUtils.decrypt(null, key)).isNull();
        assertThat(AesUtils.decrypt("", key)).isEmpty();
    }
}
