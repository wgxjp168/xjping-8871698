package com.ilbuy.common.core.utils;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.security.KeyPair;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("EncryptUtils 加密工具测试")
class EncryptUtilsTest {

    private static final String PLAIN_TEXT = "ILbuy@2024#SecretData";

    @Test
    @DisplayName("MD5 长度为 32 且一致性")
    void md5_lengthAndConsistency() {
        String hash1 = EncryptUtils.md5(PLAIN_TEXT);
        String hash2 = EncryptUtils.md5(PLAIN_TEXT);
        assertThat(hash1).hasSize(32).isEqualTo(hash2);
    }

    @Test
    @DisplayName("MD5 加盐与不加盐结果不同")
    void md5_saltDiff() {
        String hash    = EncryptUtils.md5(PLAIN_TEXT);
        String salted  = EncryptUtils.md5WithSalt(PLAIN_TEXT, "salt123");
        assertThat(hash).isNotEqualTo(salted);
    }

    @Test
    @DisplayName("SHA256 长度为 64")
    void sha256_length() {
        String hash = EncryptUtils.sha256(PLAIN_TEXT);
        assertThat(hash).hasSize(64);
    }

    @Test
    @DisplayName("AES 加解密对称")
    void aes_encryptDecrypt() {
        String key      = EncryptUtils.genAesKey();
        String cipher   = EncryptUtils.aesEncrypt(PLAIN_TEXT, key);
        String decrypted = EncryptUtils.aesDecrypt(cipher, key);
        assertThat(cipher).isNotEqualTo(PLAIN_TEXT);
        assertThat(decrypted).isEqualTo(PLAIN_TEXT);
    }

    @Test
    @DisplayName("不同密钥 AES 加密结果不同")
    void aes_differentKeys() {
        String key1 = EncryptUtils.genAesKey();
        String key2 = EncryptUtils.genAesKey();
        String enc1 = EncryptUtils.aesEncrypt(PLAIN_TEXT, key1);
        String enc2 = EncryptUtils.aesEncrypt(PLAIN_TEXT, key2);
        assertThat(enc1).isNotEqualTo(enc2);
    }

    @Test
    @DisplayName("RSA 公私钥加解密对称")
    void rsa_encryptDecrypt() {
        KeyPair kp     = EncryptUtils.genRsaKeyPair();
        String pubKey  = EncryptUtils.base64(kp.getPublic().getEncoded());
        String priKey  = EncryptUtils.base64(kp.getPrivate().getEncoded());

        String cipher  = EncryptUtils.rsaEncrypt(PLAIN_TEXT, pubKey);
        String plain   = EncryptUtils.rsaDecrypt(cipher, priKey);

        assertThat(plain).isEqualTo(PLAIN_TEXT);
    }
}
