package com.hd.common.constant;

public final class PermissionConstants {

    private PermissionConstants() {
    }

    // System admin
    public static final String SYS_ADMIN = "SYS:ADMIN";

    // User management
    public static final String SYS_USER_MGT = "SYS:USER_MGT";
    public static final String SYS_USER_VIEW = "SYS:USER:VIEW";
    public static final String SYS_USER_ADD = "SYS:USER:ADD";
    public static final String SYS_USER_EDIT = "SYS:USER:EDIT";
    public static final String SYS_USER_DELETE = "SYS:USER:DELETE";

    // Role management
    public static final String SYS_ROLE_MGT = "SYS:ROLE_MGT";
    public static final String SYS_ROLE_VIEW = "SYS:ROLE:VIEW";
    public static final String SYS_ROLE_ADD = "SYS:ROLE:ADD";
    public static final String SYS_ROLE_EDIT = "SYS:ROLE:EDIT";
    public static final String SYS_ROLE_DELETE = "SYS:ROLE:DELETE";

    // Dept management
    public static final String SYS_DEPT_MGT = "SYS:DEPT_MGT";

    // Resident management
    public static final String RESIDENT_VIEW = "RESIDENT:VIEW";
    public static final String RESIDENT_ADD = "RESIDENT:ADD";
    public static final String RESIDENT_EDIT = "RESIDENT:EDIT";
    public static final String RESIDENT_DELETE = "RESIDENT:DELETE";

    // Device management
    public static final String DEVICE_VIEW = "DEVICE:VIEW";
    public static final String DEVICE_ADD = "DEVICE:ADD";
    public static final String DEVICE_EDIT = "DEVICE:EDIT";
    public static final String DEVICE_DELETE = "DEVICE:DELETE";

    // Check management
    public static final String CHECK_VIEW = "CHECK:VIEW";
    public static final String CHECK_ADD = "CHECK:ADD";
    public static final String CHECK_EDIT = "CHECK:EDIT";
    public static final String CHECK_DELETE = "CHECK:DELETE";

    // Doctor / consultation
    public static final String DR_VIEW = "DR:VIEW";
    public static final String DR_CONSULT = "DR:CONSULT";
}
