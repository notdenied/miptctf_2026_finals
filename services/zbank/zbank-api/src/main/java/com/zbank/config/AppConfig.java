package com.zbank.config;

import io.minio.MinioClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class AppConfig {

    @Value("${minio.endpoint:http://minio:9000}")
    private String minioEndpoint;

    @Value("${minio.public-endpoint:${minio.endpoint:http://minio:9000}}")
    private String minioPublicEndpoint;

    @Value("${minio.access-key:minioadmin}")
    private String minioAccessKey;

    @Value("${minio.secret-key:minioadmin}")
    private String minioSecretKey;

    @Bean
    public MinioClient minioClient() {
        return MinioClient.builder()
                .endpoint(minioEndpoint)
                .credentials(minioAccessKey, minioSecretKey)
                .build();
    }

    @Bean("presignMinioClient")
    public MinioClient presignMinioClient() {
        return MinioClient.builder()
                .endpoint(minioPublicEndpoint)
                .credentials(minioAccessKey, minioSecretKey)
                .build();
    }

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
