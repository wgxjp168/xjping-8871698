package com.ilbuy.contract.esign;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * Mock e-signature integration service.
 * In production this would integrate with a real e-sign provider (e.g. DocuSign, 法大大, 契约锁).
 */
@Service
@Slf4j
public class ESignService {

    /**
     * Generates a contract PDF file and returns the file URL.
     *
     * @param contractNo the contract number
     * @param title      the contract title
     * @return the URL of the generated PDF
     */
    public String generateContractFile(String contractNo, String title) {
        log.info("Generating contract PDF for contractNo={}, title={}", contractNo, title);
        // Mock: return a storage URL
        return "https://storage.ilbuy.com/contracts/" + contractNo + ".pdf";
    }

    /**
     * Applies a digital seal to the signed contract and returns the sealed file URL.
     *
     * @param contractNo the contract number
     * @return the URL of the sealed PDF
     */
    public String applyDigitalSeal(String contractNo) {
        log.info("Applying digital seal for contractNo={}", contractNo);
        // Mock: return a sealed storage URL
        return "https://storage.ilbuy.com/contracts/" + contractNo + "-sealed.pdf";
    }
}
