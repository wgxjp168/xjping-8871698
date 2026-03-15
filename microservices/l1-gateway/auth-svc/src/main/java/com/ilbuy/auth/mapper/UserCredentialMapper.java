package com.ilbuy.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.ilbuy.auth.entity.UserCredential;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * 用户凭证 Mapper
 */
@Mapper
public interface UserCredentialMapper extends BaseMapper<UserCredential> {

    @Select("SELECT * FROM user_credential WHERE username = #{loginId} OR phone = #{loginId} OR email = #{loginId} LIMIT 1")
    UserCredential findByLoginId(@Param("loginId") String loginId);
}
