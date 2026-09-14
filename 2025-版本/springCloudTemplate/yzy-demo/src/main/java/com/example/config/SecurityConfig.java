package com.example.config;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Spring Security 6 配置（Boot 3）
 * <p>
 * Spring Security 6 移除了 WebSecurityConfigurerAdapter，
 * 改为暴露 SecurityFilterChain Bean + authorizeHttpRequests。
 * 放行业务接口 /api/** 与 API 文档（knife4j /doc.html、springdoc /v3/api-docs）。
 *
 * @author 杨镇宇
 * @version 2.0
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/api/**").permitAll()
                        .requestMatchers("/doc.html", "/swagger-ui.html", "/swagger-ui/**",
                                "/webjars/**", "/swagger-resources/**", "/v3/api-docs/**",
                                "/favicon.ico").permitAll()
                        .anyRequest().authenticated()
                )
                .httpBasic(basic -> {
                })
                .exceptionHandling(eh -> eh.authenticationEntryPoint((request, response, authException) -> {
                    System.out.println("Authentication failed: " + authException.getMessage());
                    response.setContentType("application/json;charset=UTF-8");
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.getWriter().write("{\"error\":\"Authentication Failed\"}");
                }));

        return http.build();
    }

}
