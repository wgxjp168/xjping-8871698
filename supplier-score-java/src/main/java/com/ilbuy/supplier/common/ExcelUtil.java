package com.ilbuy.supplier.common;

import com.alibaba.excel.EasyExcel;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

public class ExcelUtil {

    private ExcelUtil() {
    }

    public static <T> void export(HttpServletResponse response, String filename,
                                   String sheetName, Class<T> clazz, List<T> data) throws IOException {
        String encodedFilename = URLEncoder.encode(filename, StandardCharsets.UTF_8.name())
                .replaceAll("\\+", "%20");
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setCharacterEncoding("utf-8");
        response.setHeader("Content-Disposition",
                "attachment;filename*=UTF-8''" + encodedFilename + ".xlsx");
        EasyExcel.write(response.getOutputStream(), clazz)
                .sheet(sheetName)
                .doWrite(data);
    }
}
