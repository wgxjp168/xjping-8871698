package com.hd.resident.entity;

import com.baomidou.mybatisplus.annotation.*;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

@TableName("resident")
public class Resident implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 姓名 */
    private String name;

    /** 身份证号 */
    private String idCard;

    /** 性别：1=男, 2=女 */
    private Integer gender;

    /** 出生日期 */
    private LocalDate birthDate;

    /** 手机号 */
    private String phone;

    /** 住址 */
    private String address;

    /** 所属村/社区 */
    private String village;

    /** 所属乡镇/街道 */
    private String town;

    /** 所属县区 */
    private String district;

    /** 民族 */
    private String ethnicity;

    /** 血型 */
    private String bloodType;

    /** 慢病标记：高血压=1, 糖尿病=2, 精神=4 (位运算组合) */
    private Integer chronicFlag;

    /** 档案编号 */
    private String archiveNo;

    /** 所属医疗机构ID */
    private Long deptId;

    /** 状态：1=正常 */
    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getIdCard() { return idCard; }
    public void setIdCard(String idCard) { this.idCard = idCard; }
    public Integer getGender() { return gender; }
    public void setGender(Integer gender) { this.gender = gender; }
    public LocalDate getBirthDate() { return birthDate; }
    public void setBirthDate(LocalDate birthDate) { this.birthDate = birthDate; }
    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }
    public String getAddress() { return address; }
    public void setAddress(String address) { this.address = address; }
    public String getVillage() { return village; }
    public void setVillage(String village) { this.village = village; }
    public String getTown() { return town; }
    public void setTown(String town) { this.town = town; }
    public String getDistrict() { return district; }
    public void setDistrict(String district) { this.district = district; }
    public String getEthnicity() { return ethnicity; }
    public void setEthnicity(String ethnicity) { this.ethnicity = ethnicity; }
    public String getBloodType() { return bloodType; }
    public void setBloodType(String bloodType) { this.bloodType = bloodType; }
    public Integer getChronicFlag() { return chronicFlag; }
    public void setChronicFlag(Integer chronicFlag) { this.chronicFlag = chronicFlag; }
    public String getArchiveNo() { return archiveNo; }
    public void setArchiveNo(String archiveNo) { this.archiveNo = archiveNo; }
    public Long getDeptId() { return deptId; }
    public void setDeptId(Long deptId) { this.deptId = deptId; }
    public Integer getStatus() { return status; }
    public void setStatus(Integer status) { this.status = status; }
    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
    public LocalDateTime getUpdateTime() { return updateTime; }
    public void setUpdateTime(LocalDateTime updateTime) { this.updateTime = updateTime; }
    public Integer getDeleted() { return deleted; }
    public void setDeleted(Integer deleted) { this.deleted = deleted; }
}
