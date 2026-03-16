package com.ilbuy.reportgen.service.generator;

import com.ilbuy.reportgen.model.dto.GeneratedReport;
import com.ilbuy.reportgen.model.dto.ReportGenerateEvent;
import com.ilbuy.reportgen.model.enums.ClientType;

/**
 * Strategy interface – each ClientType has its own generator implementation.
 */
public interface ReportGeneratorStrategy {

    ClientType supports();

    GeneratedReport generate(ReportGenerateEvent event);
}
