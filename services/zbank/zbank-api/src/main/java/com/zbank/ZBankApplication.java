package com.zbank;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class ZBankApplication {
    public static void main(String[] args) {
        SpringApplication.run(ZBankApplication.class, args);
    }
}
