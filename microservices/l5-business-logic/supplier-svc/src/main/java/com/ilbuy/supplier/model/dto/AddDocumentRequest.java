package com.ilbuy.supplier.model.dto;

import com.ilbuy.supplier.model.enums.DocumentType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.time.LocalDate;

@Data
public class AddDocumentRequest {

    @NotNull(message = "文件类型不能为空")
    private DocumentType docType;

    @NotBlank(message = "文件名称不能为空")
    private String docName;

    @NotBlank(message = "文件URL不能为空")
    private String fileUrl;

    private LocalDate expiresAt;
}
