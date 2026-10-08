package com.example.common.tag;



import java.util.HashMap;
import java.util.Map;

public class BizContext {

    private static final ThreadLocal<Data> CONTEXT_HOLDER = new ThreadLocal<>();

    public BizContext() {

    }

    public static void init(){
        if (CONTEXT_HOLDER.get() == null){
            CONTEXT_HOLDER.set(new Data());
        }
    }

    public static boolean isInit(){
        return CONTEXT_HOLDER.get() != null;
    }

    public static void clear(){
        CONTEXT_HOLDER.remove();
    }

    public static void put(String key,Object val){
        if (CONTEXT_HOLDER.get() != null){
            CONTEXT_HOLDER.get().map.put(key, val);
        }
    }

    public static boolean contain(String key){
        return CONTEXT_HOLDER.get() != null && CONTEXT_HOLDER.get().map.containsKey(key);
    }

    public static Object get(String key){
        return CONTEXT_HOLDER.get() != null ? CONTEXT_HOLDER.get().map.get(key) : null;
    }

    private static class Data{
        private Map<String,Object> map;
        private Data(){
            this.map = new HashMap<>();
        }
    }
}
