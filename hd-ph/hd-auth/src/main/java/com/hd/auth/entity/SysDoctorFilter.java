package com.hd.auth.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 责任医生筛选条件配置实体
 */
@TableName("sys_doctor_filter")
public class SysDoctorFilter implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 筛选条件名称 */
    private String filterName;

    /** 对应字段名 */
    private String filterField;

    /** 筛选类型：TEXT/SELECT/NUMBER */
    private String filterType;

    /** 选项列表，JSON格式（SELECT类型用） */
    private String filterOptions;

    /** 排序 */
    private Integer sort;

    /** 状态：1=启用 0=禁用 */
    private Integer status;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getFilterName() { return filterName; }
    public void setFilterName(String filterName) { this.filterName = filterName; }
    public String getFilterField() { return filterField; }
    public void setFilterField(String filterField) { this.filterField = filterField; }
    public String getFilterType() { return filterType; }
    public void setFilterType(String filterType) { this.filterType = filterType; }
    public String getFilterOptions() { return filterOptions; }
    public void setFilterOptions(String filterOptions) { this.filterOptions = filterOptions; }
    public Integer getSort() { return sort; }
    public void setSort(Integer sort) { this.sort = sort; }
    public Integer getStatus() { return status; }
    public void setStatus(Integer status) { this.status = status; }
    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
    public LocalDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(LocalDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getDeleted() { return deleted; }
    public void setDeleted(Integer deleted) { this.deleted = deleted; }
}
