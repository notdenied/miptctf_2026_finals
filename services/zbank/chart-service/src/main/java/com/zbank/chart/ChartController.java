package com.zbank.chart;

import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.*;
import java.util.regex.Pattern;

@RestController
@RequestMapping("/api/chart")
public class ChartController {

    private final ExpressionParser parser = new SpelExpressionParser();

    private static final Pattern LABEL_CHARSET = Pattern.compile("^[a-zA-Z0-9.,'()=]+$");
    private static final Pattern RESERVED_FUNC = Pattern.compile("[A-Z]\\s*\\(");

    private final Map<String, Map<String, Object>> chartStore = Collections.synchronizedMap(
            new LinkedHashMap<>() {
                @Override
                protected boolean removeEldestEntry(Map.Entry<String, Map<String, Object>> eldest) {
                    return size() > 10000;
                }
            }
    );

    public static class ChartData {
        public final double totalExpenses;
        public final double totalIncome;
        public final int dataSize;
        public final Map<String, Double> categories;

        public ChartData(double totalExpenses, double totalIncome, int dataSize, Map<String, Double> categories) {
            this.totalExpenses = totalExpenses;
            this.totalIncome = totalIncome;
            this.dataSize = dataSize;
            this.categories = categories;
        }
    }

    @PostMapping("/generate")
    public ResponseEntity<?> generateChart(@RequestBody Map<String, Object> request) {
        try {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> data = (List<Map<String, Object>>) request.getOrDefault("data", new ArrayList<>());
            String message = (String) request.getOrDefault("message", "Chart");

            if (!LABEL_CHARSET.matcher(message).matches()) {
                return ResponseEntity.badRequest().body(Map.of(
                        "error", "Message contains characters not supported by the chart renderer"));
            }

            if (RESERVED_FUNC.matcher(message).find()) {
                return ResponseEntity.badRequest().body(Map.of(
                        "error", "Message conflicts with chart template syntax"));
            }

            double totalExpenses = 0;
            double totalIncome = 0;
            Map<String, Double> categoryTotals = new LinkedHashMap<>();

            for (Map<String, Object> entry : data) {
                double amount = Double.parseDouble(entry.getOrDefault("amount", "0").toString());
                String type = entry.getOrDefault("type", "expense").toString();
                String description = entry.getOrDefault("description", "Other").toString();

                if ("expense".equals(type)) {
                    totalExpenses += amount;
                } else {
                    totalIncome += amount;
                }

                String category = description.isEmpty() ? "Other" : description;
                categoryTotals.merge(category, amount, Double::sum);
            }

            StandardEvaluationContext context = new StandardEvaluationContext();
            context.setRootObject(new ChartData(totalExpenses, totalIncome, data.size(), categoryTotals));

            Object processedMessage;
            try {
                Expression exp = parser.parseExpression(message);
                processedMessage = exp.getValue(context);
            } catch (Exception e) {
                processedMessage = message;
            }

            String chartId = UUID.randomUUID().toString().replace("-", "").substring(0, 12);

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("chartId", chartId);
            result.put("message", processedMessage != null ? processedMessage.toString() : message);
            result.put("totalExpenses", totalExpenses);
            result.put("totalIncome", totalIncome);
            result.put("balance", totalIncome - totalExpenses);
            result.put("categories", categoryTotals);
            result.put("transactionCount", data.size());
            result.put("createdAt", Instant.now().toString());

            chartStore.put(chartId, result);

            return ResponseEntity.ok(result);

        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{chartId}")
    public ResponseEntity<?> getChart(@PathVariable String chartId) {
        Map<String, Object> chart = chartStore.get(chartId);
        if (chart == null) {
            return ResponseEntity.status(404).body(Map.of("error", "Chart not found"));
        }
        return ResponseEntity.ok(chart);
    }

    @GetMapping("/health")
    public ResponseEntity<?> health() {
        return ResponseEntity.ok(Map.of("status", "ok", "service", "chart-service"));
    }
}
