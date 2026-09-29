package com.example.config;

import jakarta.annotation.Resource;
import org.springframework.context.annotation.Lazy;
import org.springframework.core.MethodParameter;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerAdapter;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyAdvice;
import com.alibaba.fastjson2.support.config.FastJsonConfig;
import com.alibaba.fastjson2.support.spring6.http.converter.FastJsonHttpMessageConverter;
import java.util.List;

/**
 * 打印每次接口响应"实际选中的序列化器"，并输出 MVC 生效的转换器顺序。
 * <p>
 * 注意：不能靠 {@code @Autowired List<HttpMessageConverter<?>>} 拿转换器列表 —— 那拿到的是
 * <b>容器里 HttpMessageConverter 类型的 bean</b>（Boot 自动配置的 String / MappingJackson2 等）。
 * 而 fastjson2 转换器是在 {@code WebMvcConfigurer#extendMessageConverters} 里 new 出来直接塞进
 * {@link RequestMappingHandlerAdapter} 的列表的，不是 Spring bean，所以按类型注入永远看不到它。
 * 真正生效的列表只有 {@code requestMappingHandlerAdapter.getMessageConverters()}。
 *
 * @author yangzhenyu
 */
@ControllerAdvice
public class SerializerLogAdvice implements ResponseBodyAdvice<Object> {

    /**
     * 必须 @Lazy：RequestMappingHandlerAdapter 初始化时会去收集所有 @ControllerAdvice bean，
     * 这里再注入它就会形成循环依赖；@Lazy 注入代理对象，推迟到真正调用时才解析。
     */
    @Lazy
    @Resource
    private RequestMappingHandlerAdapter requestMappingHandlerAdapter;

    /** 转换器顺序只在首次请求时打印一次，避免刷屏 */
    private volatile boolean listPrinted = false;

    @Override
    public boolean supports(MethodParameter returnType, Class<? extends HttpMessageConverter<?>> converterType) {
        return true;
    }

    @Override
    public Object beforeBodyWrite(Object body,
                                  MethodParameter returnType,
                                  MediaType selectedContentType,
                                  Class<? extends HttpMessageConverter<?>> selectedConverterType,
                                  ServerHttpRequest request,
                                  ServerHttpResponse response) {

        System.out.println("\n===== 本次接口序列化 =====");
        System.out.println("选中Converter Class: " + selectedConverterType.getName());
        System.out.println("接口返回对象类型: " + (body == null ? "null" : body.getClass().getName()));
        System.out.println("==========================");

        if (!listPrinted) {
            listPrinted = true;
            System.out.println("---- RequestMappingHandlerAdapter 真实转换器顺序 ----");
            List<HttpMessageConverter<?>> converters = requestMappingHandlerAdapter.getMessageConverters();
            for (int i = 0; i < converters.size(); i++) {
                HttpMessageConverter<?> converter = converters.get(i);
                System.out.println("  [" + i + "] " + converter.getClass().getName());
                if (converter instanceof FastJsonHttpMessageConverter fc) {
                    FastJsonConfig cfg = fc.getFastJsonConfig();
                    System.out.println("       -> WriterFeatures = " + java.util.Arrays.toString(cfg.getWriterFeatures())
                            + ", WriterFilters = " + java.util.Arrays.toString(cfg.getWriterFilters())
                            + ", supportedMediaTypes = " + fc.getSupportedMediaTypes());
                }
            }
            System.out.println("----------------------------------------------------\n");
        }
        return body;
    }
}