package com.zbank.security;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * Filter that checks for X-Local-Job header on internal endpoints.
 * This header is blocked by lighttpd from external requests,
 * so only internal background jobs can access /api/internal/* endpoints.
 */
@Component
@Order(1)
public class LocalJobFilter implements Filter {

    private static final String LOCAL_JOB_HEADER = "X-Local-Job";
    private static final String LOCAL_JOB_SECRET = "zbank-internal-job-secret-2024";

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        String path = httpRequest.getRequestURI();

        if (path.startsWith("/api/internal/")) {
            String jobHeader = httpRequest.getHeader(LOCAL_JOB_HEADER);
            if (!LOCAL_JOB_SECRET.equals(jobHeader)) {
                HttpServletResponse httpResponse = (HttpServletResponse) response;
                httpResponse.setStatus(HttpServletResponse.SC_FORBIDDEN);
                httpResponse.getWriter().write("{\"error\":\"Access denied\"}");
                return;
            }
        }

        chain.doFilter(request, response);
    }
}
