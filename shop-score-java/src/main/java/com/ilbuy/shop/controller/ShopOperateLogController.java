package com.ilbuy.shop.controller;

import com.ilbuy.shop.common.ExcelUtil;
import com.ilbuy.shop.common.PageResult;
import com.ilbuy.shop.common.Result;
import com.ilbuy.shop.dto.ShopLogQueryDTO;
import com.ilbuy.shop.service.ShopOperateLogService;
import com.ilbuy.shop.vo.ShopOperateLogVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 操作日志查询（只读，写入由各 Service 内部调用）
 */
@RestController
@RequestMapping("/shop/log")
@RequiredArgsConstructor
public class ShopOperateLogController {

    private final ShopOperateLogService logService;

    /**
     * 分页查询
     * GET /shop/log/page?shopId=&operateType=&operateUser=&operateTimeStart=&operateTimeEnd=
     */
    @GetMapping("/page")
    public Result<PageResult<ShopOperateLogVO>> page(@Validated ShopLogQueryDTO query) {
        return Result.ok(logService.page(query));
    }

    /**
     * 导出 Excel
     */
    @GetMapping("/export")
    public void export(ShopLogQueryDTO query, HttpServletResponse response) throws IOException {
        ExcelUtil.export(response, "操作日志", "日志",
            ShopOperateLogVO.class, logService.listForExport(query));
    }
}
