package com.example.api.vo;

import lombok.Data;

import java.io.Serializable;

/**
 * api sdk 测试接口出参
 *
 * @author yangzhenyu
 * @version 1.0
 */
@Data
public class ApiSdkVoRep implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;

    private String name;
}
