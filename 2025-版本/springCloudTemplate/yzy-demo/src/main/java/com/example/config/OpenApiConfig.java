package com.example.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * OpenAPI3 (springdoc + knife4j4) 配置
 * <p>
 * 替代原 springfox SwaggerConfig：springfox 基于 Spring5/javax，
 * 无法在 Spring Boot 3 / Jakarta 下工作。
 * <ul>
 *     <li>knife4j UI：/doc.html</li>
 *     <li>springdoc 原生 UI：/swagger-ui.html</li>
 *     <li>OpenAPI json：/v3/api-docs</li>
 * </ul>
 *
 * @author yangzhenyu
 * @version 2.0
 */
@Configuration
public class OpenApiConfig {
    private static final Logger log = LoggerFactory.getLogger(OpenApiConfig.class);

    public OpenApiConfig() {
        log.info("===================集成OpenAPI3(Knife4j)配置===================");
    }

    /**
     * 创建 OpenAPI 文档摘要信息
     */
    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("接口文档")
                        .description("描述：接口")
                        .version("版本号:1.0.0")
                        .contact(new Contact().name("yangzhenyu").email("xxx@ccbscf.com"))
                        //http://127.0.0.1:8088/doc.html
                        .termsOfService("http://{ip}:{port}/doc.html"));
    }
}
