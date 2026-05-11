---
name: seed
description: 初始化数据库种子数据（角色、管理员账号）
---

## 初始化种子数据

```bash
cd backend && python scripts/seed.py
```

### 创建的内容
1. **默认角色**：user（普通用户）、lawyer（法律专家）、admin（管理员）
2. **管理员账号**：admin@example.com（密码在 seed 脚本中配置）
3. **初始权限数据**

### 注意事项
- 仅在首次部署或重置数据库后运行
- 重复运行不会重复创建（幂等设计）
