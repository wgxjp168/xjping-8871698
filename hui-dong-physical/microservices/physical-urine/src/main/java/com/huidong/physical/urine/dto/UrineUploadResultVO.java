package com.huidong.physical.urine.dto;

import lombok.Data;

/**
 * 尿常规上传响应
 */
@Data
public class UrineUploadResultVO {

    /** 上传ID（回传） */
    private String uploadId;

    /** 处理状态 ACCEPTED=已接收 DUPLICATE=重复上传已忽略 */
    private String status;

    /** 体检单ID（已创建或匹配的） */
    private Long examRecordId;

    /** 提示信息 */
    private String message;
}
