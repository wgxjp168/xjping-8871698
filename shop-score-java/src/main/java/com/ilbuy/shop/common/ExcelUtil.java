package com.ilbuy.shop.common;

import com.alibaba.excel.EasyExcel;
import com.alibaba.excel.write.style.column.LongestMatchColumnWidthStyleStrategy;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * EasyExcel 导出工具
 */
public class ExcelUtil {

    private ExcelUtil() {}

    /**
     * 将数据写入 HTTP 响应流（浏览器直接下载）
     *
     * @param response  HttpServletResponse
     * @param filename  文件名（不含扩展名）
     * @param sheetName sheet名
     * @param clazz     EasyExcel 模板类（需要 @ExcelProperty 注解）
     * @param data      数据列表
     */
    public static <T> void export(HttpServletResponse response,
                                  String filename,
                                  String sheetName,
                                  Class<T> clazz,
                                  List<T> data) throws IOException {
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setCharacterEncoding("utf-8");
        String encodedName = URLEncoder.encode(filename, StandardCharsets.UTF_8.name())
                                       .replaceAll("\\+", "%20");
        response.setHeader("Content-Disposition",
            "attachment;filename*=UTF-8''" + encodedName + ".xlsx");

        EasyExcel.write(response.getOutputStream(), clazz)
                 .registerWriteHandler(new LongestMatchColumnWidthStyleStrategy())
                 .sheet(sheetName)
                 .doWrite(data);
    }
}
