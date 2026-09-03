package com.example.utils;

public class SingletonStorage {
    // 静态变量，保存单例对象
    private static SingletonStorage instance;

    // 存储变量字段
    private String numberSwitch;
    private SingletonStorage() {
        // 给变量赋默认值
        this.numberSwitch = "false";
    }

    // 静态方法，获取唯一的实例
    public static SingletonStorage getInstance() {
        if (instance == null) {
            synchronized (SingletonStorage.class) {
                if (instance == null) {
                    instance = new SingletonStorage();
                }
            }
        }
        return instance;
    }

    // 提供 getter 和 setter 方法来访问和修改变量
    public void setNumberSwitch(String numberSwitch){
        this.numberSwitch = numberSwitch;
    }
    public String getNumberSwitch(){
        return numberSwitch;
    }
}
