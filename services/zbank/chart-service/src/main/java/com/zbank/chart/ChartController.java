package com.zbank.chart;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.jfree.chart.ChartFactory;
import org.jfree.chart.ChartUtils;
import org.jfree.chart.JFreeChart;
import org.jfree.chart.plot.PiePlot;
import org.jfree.data.general.DefaultPieDataset;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.time.Instant;
import java.util.*;
import java.util.Base64;

@RestController
@RequestMapping("/api/chart")
public class ChartController {

    private final ExpressionParser parser = new SpelExpressionParser();

    private static final java.util.regex.Pattern LABEL_CHARSET =
            java.util.regex.Pattern.compile("^[\\w\\s.,'():| ₽+\\-]+$");

    private static final java.util.regex.Pattern RESERVED_PATTERNS =
            java.util.regex.Pattern.compile("T\\s*\\(|@[a-zA-Z]|\\bnew\\s+[A-Z]");

    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final String CHART_KEY_PREFIX = "chart:";

    private static final String CHART_INDEX_KEY = "chart:index";

    @Value("${chart.store.max-size:10000}")
    private int maxSize;

    public ChartController(StringRedisTemplate redis) {
        this.redis = redis;
    }

    // ── Domain object for expressions ─────────────────────────────

    public static class ChartData {
        public final double totalExpenses;
        public final double totalIncome;
        public final double balance;
        public final double maxExpense;
        public final double maxIncome;
        public final double averageTransaction;
        public final int transactionCount;
        public final int dataSize;
        public final Map<String, Double> categories;

        public ChartData(double totalExpenses, double totalIncome,
                         double maxExpense, double maxIncome,
                         double averageTransaction, int dataSize,
                         Map<String, Double> categories) {
            this.totalExpenses = totalExpenses;
            this.totalIncome = totalIncome;
            this.balance = totalIncome - totalExpenses;
            this.maxExpense = maxExpense;
            this.maxIncome = maxIncome;
            this.averageTransaction = averageTransaction;
            this.transactionCount = dataSize;
            this.dataSize = dataSize;
            this.categories = categories;
        }
    }

    // ── Endpoints ─────────────────────────────────────────────────────────────

    @PostMapping("/generate")
    public ResponseEntity<?> generateChart(@RequestBody Map<String, Object> request) {
        try {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> data =
                    (List<Map<String, Object>>) request.getOrDefault("data", new ArrayList<>());
            String message = (String) request.getOrDefault("message", "'Chart'");

            // Validate the message expression before evaluation
            if (!LABEL_CHARSET.matcher(message).matches()) {
                return ResponseEntity.badRequest().body(Map.of(
                        "error", "Message contains unsupported characters"));
            }
            if (RESERVED_PATTERNS.matcher(message).find()) {
                return ResponseEntity.badRequest().body(Map.of(
                        "error", "Message contains reserved expression patterns"));
            }

            // ── Aggregate transaction data ────────────────────────────────────

            double totalExpenses = 0, totalIncome = 0, maxExpense = 0, maxIncome = 0;
            Map<String, Double> categoryTotals = new LinkedHashMap<>();

            for (Map<String, Object> entry : data) {
                double amount = Double.parseDouble(entry.getOrDefault("amount", "0").toString());
                String type = entry.getOrDefault("type", "expense").toString();
                String description = entry.getOrDefault("description", "Other").toString();

                if ("expense".equals(type)) {
                    totalExpenses += amount;
                    if (amount > maxExpense) maxExpense = amount;
                } else {
                    totalIncome += amount;
                    if (amount > maxIncome) maxIncome = amount;
                }
                categoryTotals.merge(description.isEmpty() ? "Other" : description, amount, Double::sum);
            }

            double averageTransaction = data.isEmpty() ? 0 : (totalExpenses + totalIncome) / data.size();

            // ── Evaluate title expression ────────────────────────────────
            StandardEvaluationContext ctx = new StandardEvaluationContext();
            ctx.setRootObject(new ChartData(
                    totalExpenses, totalIncome, maxExpense, maxIncome,
                    averageTransaction, data.size(), categoryTotals));

            Object processedMessage;
            try {
                Expression exp = parser.parseExpression(message);
                processedMessage = exp.getValue(ctx);
            } catch (Exception e) {
                processedMessage = message;
            }

            // ── Generate pie chart image ──────────────────────────────────────
            String base64Image = "";
            try {
                DefaultPieDataset dataset = new DefaultPieDataset();
                categoryTotals.forEach(dataset::setValue);

                JFreeChart jfreechart = ChartFactory.createPieChart(
                        processedMessage != null ? processedMessage.toString() : message,
                        dataset, true, true, false);

                jfreechart.setBackgroundPaint(new Color(5, 5, 5));
                jfreechart.getTitle().setPaint(Color.WHITE);
                jfreechart.getLegend().setBackgroundPaint(new Color(20, 20, 20));
                jfreechart.getLegend().setItemPaint(Color.WHITE);

                PiePlot plot = (PiePlot) jfreechart.getPlot();
                plot.setBackgroundPaint(new Color(20, 20, 20));
                plot.setLabelBackgroundPaint(new Color(40, 40, 40));
                plot.setLabelPaint(Color.WHITE);
                plot.setOutlineVisible(false);
                plot.setShadowPaint(null);

                ByteArrayOutputStream out = new ByteArrayOutputStream();
                ChartUtils.writeChartAsPNG(out, jfreechart, 600, 400);
                base64Image = Base64.getEncoder().encodeToString(out.toByteArray());
            } catch (Exception ex) {
                ex.printStackTrace();
            }

            // ── Build result ──────────────────────────────────────────────────
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
            result.put("imageBase64", base64Image);

            // ── Persist to Redis ──────────────────────────────────────────────
            storeChart(chartId, result);

            return ResponseEntity.ok(result);

        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{chartId}")
    public ResponseEntity<?> getChart(@PathVariable String chartId) {
        try {
            String json = redis.opsForValue().get(CHART_KEY_PREFIX + chartId);
            if (json == null) {
                return ResponseEntity.status(404).body(Map.of("error", "Chart not found"));
            }
            Map<String, Object> chart = objectMapper.readValue(json, new TypeReference<>() {});
            return ResponseEntity.ok(chart);
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", "Failed to retrieve chart"));
        }
    }

    @GetMapping("/health")
    public ResponseEntity<?> health() {
        return ResponseEntity.ok(Map.of("status", "ok", "service", "chart-service"));
    }

    // ── Storage helpers ───────────────────────────────────────────────────────

    /**
     * Stores the chart in Redis and maintains an insertion-order index.
     * When the store exceeds maxSize, the oldest entries are evicted (LRU-like by insertion time).
     */
    private void storeChart(String chartId, Map<String, Object> result) {
        try {
            String json = objectMapper.writeValueAsString(result);
            redis.opsForValue().set(CHART_KEY_PREFIX + chartId, json);

            // Track insertion order via a sorted set (score = current epoch millis)
            double score = System.currentTimeMillis();
            redis.opsForZSet().add(CHART_INDEX_KEY, chartId, score);

            // Evict oldest entries if we exceed the limit
            long size = Optional.ofNullable(redis.opsForZSet().zCard(CHART_INDEX_KEY)).orElse(0L);
            if (size > maxSize) {
                long toRemove = size - maxSize;
                Set<String> oldest = redis.opsForZSet().range(CHART_INDEX_KEY, 0, toRemove - 1);
                if (oldest != null) {
                    for (String oldId : oldest) {
                        redis.delete(CHART_KEY_PREFIX + oldId);
                    }
                    redis.opsForZSet().removeRange(CHART_INDEX_KEY, 0, toRemove - 1);
                }
            }
        } catch (Exception e) {
            // Log but don't fail the request if Redis write fails
            e.printStackTrace();
        }
    }
}
