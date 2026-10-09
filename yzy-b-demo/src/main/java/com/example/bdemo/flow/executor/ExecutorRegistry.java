package com.example.bdemo.flow.executor;


import org.springframework.stereotype.Component;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class ExecutorRegistry {
    private final Map<String, BaseExecutor> executorMap = new ConcurrentHashMap<>();

    public void register(String key, BaseExecutor executor) {
        executorMap.put(key, executor);
    }

    @SuppressWarnings("unchecked")
    public <T extends BaseExecutor> T get(String key, Class<T> clazz) {
        return (T) executorMap.get(key);
    }
}