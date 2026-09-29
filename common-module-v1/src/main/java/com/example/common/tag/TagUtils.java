package com.example.common.tag;


import com.alibaba.nacos.common.utils.StringUtils;
import com.example.bdemo.flow.tag.BizContext;

import java.util.List;

public class TagUtils {

    private static final String TAG = "center_tag";
    private static final String PRE_TRANSLATION = "pre_translation";

    public TagUtils() {
    }

    public static String getChannelTag(){
        if (!BizContext.isInit()){
            BizContext.init();
        }
        return BizContext.contain(TAG) && BizContext.get(TAG) != null ? (String) BizContext.get(TAG) : null;
    }

    public static String getPreTranslation(){
        if (!BizContext.isInit()){
            BizContext.init();
        }
        return BizContext.contain(PRE_TRANSLATION) && BizContext.get(PRE_TRANSLATION) != null ? (String) BizContext.get(PRE_TRANSLATION) : null;
    }

    public static void updatePreTranslation(List<String> nodes){
        if (nodes != null && !nodes.isEmpty()){
            if (!BizContext.isInit()){
                BizContext.init();
            }
            BizContext.put(PRE_TRANSLATION,nodes);
        }else {
            Thread thread = Thread.currentThread();
            throw new RuntimeException("当前线程【"+thread.getName()+"】,更新center tag为空");
        }
    }

    public static void updateChannelCenterTag(String center){
        if (StringUtils.isNotBlank(center)){
            if (!BizContext.isInit()){
                BizContext.init();
            }
            BizContext.put(TAG,center);
        }else {
            Thread thread = Thread.currentThread();
            throw new RuntimeException("当前线程【"+thread.getName()+"】,更新center tag为空");
        }
    }

    public static void clear(){
        if (BizContext.isInit()){
            BizContext.clear();
        }
    }
}