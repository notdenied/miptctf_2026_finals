package com.zbank.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChartService {

    @Value("${chart.service.url:http://chart-service:8081}")
    private String chartServiceUrl;

    private final RestTemplate restTemplate;

    @SuppressWarnings("unchecked")
    public Map<String, Object> generateSpendingChart(List<Map<String, Object>> spendingData, String message) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("data", spendingData);
            request.put("message", message);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);

            ResponseEntity<Map> response = restTemplate.exchange(
                    chartServiceUrl + "/api/chart/generate",
                    HttpMethod.POST,
                    entity,
                    Map.class
            );

            return response.getBody();
        } catch (Exception e) {
            log.error("Chart service call failed", e);
            throw new RuntimeException("Chart service unavailable: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getChart(String chartId) {
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(
                    chartServiceUrl + "/api/chart/" + chartId,
                    Map.class
            );
            return response.getBody();
        } catch (Exception e) {
            log.error("Chart service call failed", e);
            throw new RuntimeException("Chart service unavailable: " + e.getMessage());
        }
    }
}
