package com.example.api.feign;

import com.example.api.config.FeignFastJsonCodecConfig;
import com.example.api.vo.ApiSdkVoRep;
import com.example.api.vo.ApiSdkVoRes;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

/**
 * yzy-demo 对外暴露的 api sdk 测试接口（OpenFeign 声明式客户端）
 *
 * <p>使用方接入三步：
 * <ol>
 *   <li>pom 引入 {@code com.example:yzy-demo-api}（版本已在 yzy-dependencies-bom 管理，无需写版本号）；</li>
 *   <li>启动类 {@code @EnableFeignClients(basePackages = {"...自身feign包", "com.example.api.feign"})}；</li>
 *   <li>{@code @Resource TestApiClient testApiClient;} 直接注入调用。</li>
 * </ol>
 *
 * <p>契约说明：本接口由 yzy-demo 的 TestApiController 实现，服务端改签名会直接编译失败，
 * 避免出现「接口改了、SDK 没同步」的线上问题。
 *
 * <p>编解码：通过 {@code configuration = FeignFastJsonCodecConfig.class} 指定该客户端用 fastjson，
 * 这是<b>客户端级</b>配置，只影响 TestApiClient，不会波及使用方自己的其他 Feign 客户端。
 * 如果某个使用方不想用 fastjson，改成自己的配置类即可（删掉 configuration 属性，
 * 或在自己的 @FeignClient 上另指一个）。
 *
 * @author yangzhenyu
 * @version 1.0
 */
@FeignClient(name = "yzy-demo", contextId = "testApiClient", path = "/api/sdk",
        configuration = FeignFastJsonCodecConfig.class)
public interface TestApiClient {

    /**
     * 调用 yzy-demo 的 /api/sdk/apiTest 接口
     *
     * @param req 入参（id）
     * @return 出参（id、name）
     */
    @PostMapping("/apiTest")
    ApiSdkVoRep apiTest(@RequestBody ApiSdkVoRes req);
}
