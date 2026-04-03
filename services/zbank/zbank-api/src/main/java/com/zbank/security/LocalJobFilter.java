package com.zbank.security;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Component
@Order(1)
public class LocalJobFilter implements Filter {

    private static final String LOCAL_JOB_HEADER = "X-Local-Job";

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        String path = httpRequest.getRequestURI().toLowerCase();

        if (path.startsWith("/api/internal/")) {
            String jobHeader = httpRequest.getHeader(LOCAL_JOB_HEADER);
            if (jobHeader == null || !jobHeader.equals("true")) {
                HttpServletResponse httpResponse = (HttpServletResponse) response;
                httpResponse.setStatus(HttpServletResponse.SC_FORBIDDEN);
                httpResponse.getWriter().write("{\"error\":\"Access denied\"}");
                return;
            }
        }

        chain.doFilter(request, response);
    }
}
